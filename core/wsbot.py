import asyncio
import json
import traceback

import websockets
import websockets.exceptions
import websockets.server
import threading

from manager.timer_manager import timer_manager
from common.message_process import messageprocess
from common.config import config
from common.log import logger
from core.globals import glob_instance
from utils.Job import Job


class WebSocketManager:
    def __init__(self):
        self.alive = False

    async def handle_websocket(self, client_id):
        """
        处理WebSocket连接的异步函数。

        该函数在接收到WebSocket消息后进行处理，包括日志记录、消息解析、过滤管理和插件管理。

        参数:
        - websocket: WebSocket连接对象。
        - client_id: 客户端标识符，用于标识连接的客户端。

        返回值:
        无返回值。该函数通过异步方式执行，并在连接关闭时结束。
        """
        try:
            threading.Thread(target=timer_manager.handle_command, args=(glob_instance.ws, config["timer_gids_list"])).start()
            # 主循环，持续接收并处理WebSocket消息
            while True:
                if not self.alive:
                    logger.debug("收到进程结束通知，WS已关闭")
                    return

                # 记录接收到的服务器数据日志
                message = json.loads(await glob_instance.ws.recv())
                messageprocess.add_message(glob_instance.ws, message)

        # 捕获WebSocket连接关闭异常
        except websockets.exceptions.ConnectionClosedError as error:
            logger.error(f"WebSocket连接关闭异常: {error}")
            # 捕获其他所有异常
        except Exception as error:
            logger.error(f"发生错误: {error}")
            print(traceback.format_exc())
            # 确保在函数结束前关闭WebSocket连接
        finally:
            await glob_instance.ws.close()
            glob_instance.ws = None
            logger.error(f"客户端 {client_id} 断开连接")

    # 异步函数启动WebSocket服务器
    async def start_websocket_server(self):
        # 检查配置中是否缺少必要的键值对
        if "websocket_uri" not in config or "websocket_port" not in config:
            logger.error("连接配置缺少必要键值对，请检查配置文件.")
            return

        # 从配置中获取WebSocket的URI和端口号
        uri = config["websocket_uri"]
        port = config["websocket_port"]

        # 标记是否继续尝试连接
        continue_connecting = True
        # 初始化失败尝试次数计数器
        flag = 0
        websocket_url = "<Unknown>"
        while continue_connecting and self.alive:
            try:
                # 构建WebSocket URL，如果配置中有token，则加入到URL中
                if "token" in config:
                    # 使用get方法确保即使'token'不存在也不会抛出异常
                    access_token = config.get('token', '')
                    websocket_url = f"{uri}:{port}?access_token={access_token}"
                else:
                    websocket_url = f"{uri}:{port}"
                # 使用 async with 确保 server 正确关闭
                async with websockets.connect(websocket_url) as websocket:
                    # 启动协程处理 WebSocket
                    glob_instance.ws = websocket
                    flag = 0
                    task = asyncio.create_task(self.handle_websocket(1))
                    await task

            # 捕获连接意外关闭的异常
            except websockets.exceptions.ConnectionClosedError as error:
                logger.error(f"WebSocket 连接意外关闭: {error} URL: {websocket_url}")
            # 捕获无效状态码异常
            except websockets.exceptions.InvalidStatusCode as error:
                logger.error(f"收到无效的状态码: {error} URL: {websocket_url}")
            # 捕获其他所有异常
            except Exception as error:
                logger.error(f"启动 WebSocket 服务器失败: {error} URL: {websocket_url}")
                await asyncio.sleep(1)
                flag += 1

            # 如果失败尝试次数超过5次，则停止连接尝试
            if flag >= 5:
                logger.error("多次尝试后无法连接到 WebSocket 服务器.")
                continue_connecting = False

    def run_websocket_server(self):
        if self.alive:
            return
        self.alive = True
        asyncio.run(self.start_websocket_server())

    def create_job(self):
        # 创建并运行WebSocket服务器线程
        ws_thread = Job(target=self.run_websocket_server)
        ws_thread.daemon = True  # 设置线程为守护线程，以便在主程序停止时自动关闭
        return ws_thread


ws_manager = WebSocketManager()
