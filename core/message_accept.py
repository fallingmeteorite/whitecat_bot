import asyncio
import json
import os
import signal
import sys
import threading
import time
import weakref
from typing import Optional, Any

import websockets
import websockets.exceptions

from common import logger
from config import config
from message_action import message_processor
from plugin_processing import timer_manager
from task_scheduling import shutdown


class WebSocketManager:
    """
    WebSocket 管理器类，负责 WebSocket 连接的建立、消息处理和异常处理。
    """
    # 消息控制
    websocket_stop = False
    websocket_stopping = False

    def __init__(self):
        """
        初始化 WebSocket 管理器。
        """
        self.alive = False  # 标记服务器是否运行
        self.loop: Optional[asyncio.AbstractEventLoop] = None  # 存储事件循环
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None  # WebSocket 连接对象

        # 注册信号处理函数
        signal.signal(signal.SIGINT, self.handle_signal)  # 处理 Ctrl+C
        signal.signal(signal.SIGTERM, self.handle_signal)  # 处理终止信号

    async def handle_websocket(self, client_id: int) -> None:
        """
        处理 WebSocket 连接的异步函数。

        Args:
            client_id: 客户端 ID。
        """
        # 使用弱引用存储 WebSocket 对象
        websocket_ref = weakref.ref(self.websocket)

        # 启动定时器任务
        threading.Thread(
            target=timer_manager.handle_command,
            args=(websocket_ref(), config["timer_gids_list"]),
            daemon=True
        ).start()

        try:
            while self.alive:
                # 接收并处理消息
                websocket = websocket_ref()
                if websocket and not self.websocket_stop:
                    if self.websocket_stopping:
                        self.websocket_stopping = False
                    message = json.loads(await websocket.recv())
                    message_processor.add_message(websocket, message)
                else:
                    if not self.websocket_stopping:
                        self.websocket_stopping = True
                    await asyncio.sleep(2)
        except Exception as error:
            logger.error(f"发生错误: {error}")
        finally:
            # 关闭 WebSocket 连接
            websocket = websocket_ref()
            if websocket:
                await websocket.close()
                self.websocket = None
            logger.error(f"客户端 {client_id} 断开连接")

    async def start_websocket_server(self) -> None:
        """
        启动 WebSocket 服务器的异步函数。
        """
        if "websocket_uri" not in config or "websocket_port" not in config:
            logger.error("连接配置缺少必要键值对，请检查配置文件.")
            return

        uri = config["websocket_uri"]
        port = config["websocket_port"]

        continue_connecting = True
        retry_count = 0
        websocket_url = "<Unknown>"

        while continue_connecting and self.alive:
            try:
                # 构建 WebSocket 连接 URL
                if "token" in config:
                    access_token = config.get('token', '')
                    websocket_url = f"{uri}:{port}?access_token={access_token}"
                else:
                    websocket_url = f"{uri}:{port}"

                # 建立 WebSocket 连接
                async with websockets.connect(websocket_url) as self.websocket:
                    task = asyncio.create_task(self.handle_websocket(1))
                    await task

            except websockets.exceptions.ConnectionClosedError as error:
                logger.error(f"WebSocket 连接意外关闭: {error} URL: {websocket_url}")
            except Exception as error:
                logger.error(f"启动 WebSocket 服务器失败: {error} URL: {websocket_url}")
                await asyncio.sleep(1)
                retry_count += 1

            if retry_count >= 5:
                logger.error("多次尝试后无法连接到 WebSocket 服务器.")
                continue_connecting = False

    def run_websocket_server(self) -> None:
        """
        运行 WebSocket 服务器。
        """
        if self.alive:
            return
        self.alive = True
        self.loop = asyncio.new_event_loop()  # 创建新的事件循环
        asyncio.set_event_loop(self.loop)  # 设置为当前线程的事件循环
        self.loop.run_until_complete(self.start_websocket_server())

    def handle_signal(self, signum: int, frame: Any) -> None:
        """
        处理信号（如 Ctrl+C 或终止信号），优雅地停止应用。

        Args:
            signum: 信号编号。
            frame: 当前的堆栈帧。
        """
        logger.info(f"接收到信号 {signum}，停止应用...")
        self.alive = False
        if self.loop:
            self.loop.stop()
        logger.warning("正在等待运行任务结束,请耐心等待")
        shutdown(True)
        sys.exit()


def file_monitor() -> None:
    """
    文件监控进程，检查环境变量并在满足条件时停止 WebSocket 应用。
    """
    while True:
        try:
            if os.path.exists("./websocket_stop.txt"):
                if not ws_manager.websocket_stop:
                    ws_manager.websocket_stop = True
                if ws_manager.websocket_stopping:
                    os.remove("websocket_stop.txt")

            if os.path.exists("./restart_wsbot.txt"):
                logger.info("监控到停止条件，准备停止 wsbot 应用...")
                os.kill(os.getpid(), signal.SIGTERM)
                os.remove("restart_wsbot.txt")
                break
            time.sleep(2.0)  # 每隔2秒检查一次文件
        except KeyboardInterrupt:
            break


def main() -> None:
    """
    主函数，启动文件监控进程和 WebSocket 服务器。
    """
    # 启动文件监控进程
    threading.Thread(target=file_monitor, daemon=True).start()
    # 运行 WebSocket 服务器
    ws_manager.run_websocket_server()


# 全局实例
ws_manager = WebSocketManager()

try:
    main()
except KeyboardInterrupt:
    logger.info("应用已手动停止。")
