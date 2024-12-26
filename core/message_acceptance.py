import asyncio
import json
import os
import signal
import sys
import threading
import time

import websockets
import websockets.exceptions

from common.config import config
from common.logging import logger
from common.message_process import messageprocess
from common.message_send import send_message
from manager.timer_manager import timer_manager


class WebSocketManager:
    def __init__(self):
        self.alive = False  # 标记服务器是否运行
        self.loop = None  # 存储事件循环
        self.websocket = None

        # 注册信号处理函数
        signal.signal(signal.SIGINT, self.handle_signal)  # 处理 Ctrl+C
        signal.signal(signal.SIGTERM, self.handle_signal)  # 处理终止信号

    async def handle_websocket(self, client_id):
        """
        处理 WebSocket 连接的异步函数。
        """
        flag = 0
        while True:
            flag += 1
            if flag > 4:
                break
            if os.path.exists("./restart.txt"):
                with open("./restart.txt", "r") as f:  # 打开文件
                    data = f.read().split(",")  # 读取文件
                send_message(self.websocket, None, data[1], message=f"服务器重启完毕,花费时间为: {data[2]} s")
                os.remove("./restart.txt")
                break
            time.sleep(0.5)
        flag = None
        threading.Thread(target=timer_manager.handle_command, args=(self.websocket, config["timer_gids_list"]),
                         daemon=True).start()  # 启动定时器
        try:
            while self.alive:
                message = json.loads(await self.websocket.recv())
                messageprocess.add_message(self.websocket, message)
        except Exception as error:
            logger.error(f"发生错误: {error}")
        finally:
            await self.websocket.close()
            self.websocket = None
            logger.error(f"客户端 {client_id} 断开连接")

    async def start_websocket_server(self):
        """
        启动 WebSocket 服务器的异步函数。
        """
        if "websocket_uri" not in config or "websocket_port" not in config:
            logger.error("连接配置缺少必要键值对，请检查配置文件.")
            return

        uri = config["websocket_uri"]
        port = config["websocket_port"]

        continue_connecting = True
        flag = 0
        websocket_url = "<Unknown>"
        while continue_connecting and self.alive:
            try:
                if "token" in config:
                    access_token = config.get('token', '')
                    websocket_url = f"{uri}:{port}?access_token={access_token}"
                else:
                    websocket_url = f"{uri}:{port}"

                async with websockets.connect(websocket_url) as self.websocket:
                    task = asyncio.create_task(self.handle_websocket(1))
                    await task

            except websockets.exceptions.ConnectionClosedError as error:
                logger.error(f"WebSocket 连接意外关闭: {error} URL: {websocket_url}")
            except websockets.exceptions.InvalidStatusCode as error:
                logger.error(f"收到无效的状态码: {error} URL: {websocket_url}")
            except Exception as error:
                logger.error(f"启动 WebSocket 服务器失败: {error} URL: {websocket_url}")
                await asyncio.sleep(1)
                flag += 1

            if flag >= 5:
                logger.error("多次尝试后无法连接到 WebSocket 服务器.")
                continue_connecting = False

    def run_websocket_server(self):
        """
        运行 WebSocket 服务器。
        """
        if self.alive:
            return
        self.alive = True
        self.loop = asyncio.new_event_loop()  # 创建新的事件循环
        asyncio.set_event_loop(self.loop)  # 设置为当前线程的事件循环
        self.loop.run_until_complete(self.start_websocket_server())

    def handle_signal(self, signum, frame):
        """
        处理信号（如 Ctrl+C 或终止信号）。
        """
        logger.info(f"接收到信号 {signum}，停止应用...")
        self.alive = False
        sys.exit(0)


def file_monitor():
    """
    文件监控进程，检查文件内容并在满足条件时停止 FastAPI 应用。
    """
    while True:
        try:
            if os.path.exists("./restart_wsbot.txt"):
                with open("./restart_wsbot.txt", "r") as file:
                    if file.read().strip() == "restart":
                        logger.info("监控到停止条件，准备停止 wsbot 应用...")
                        os.kill(os.getpid(), signal.SIGTERM)
                        os.remove("restart_wsbot.txt")
                        break
            time.sleep(2)  # 每隔2秒检查一次文件
        except KeyboardInterrupt:
            break


def main():
    # 启动监控进程
    threading.Thread(target=file_monitor, daemon=True).start()
    # 运行 WebSocket 服务器
    ws_manager.run_websocket_server()


# 全局实例
ws_manager = WebSocketManager()
try:
    main()
except KeyboardInterrupt:
    pass
