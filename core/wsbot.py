import asyncio
import json

import websockets
import websockets.exceptions

from common.config import config
from common.log import logger
from common.message_process import messageprocess
from core.globals import glob_instance
from utils.thread_creation import ThreadController


class WebSocketManager:
    def __init__(self):
        self.alive = False  # 标记服务器是否运行
        self.loop = None  # 存储事件循环
        self.tasks = set()  # 存储所有异步任务

    async def handle_websocket(self, client_id):
        """
        处理 WebSocket 连接的异步函数。
        """
        try:
            while self.alive:
                message = json.loads(await glob_instance.ws.recv())
                messageprocess.add_message(glob_instance.ws, message)
        except Exception as error:
            logger.error(f"发生错误: {error}")
        finally:
            await glob_instance.ws.close()
            glob_instance.ws = None
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

                async with websockets.connect(websocket_url) as websocket:
                    glob_instance.ws = websocket
                    flag = 0
                    task = asyncio.create_task(self.handle_websocket(1))
                    self.tasks.add(task)  # 将任务添加到集合中
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

    def create_job(self):
        """
        创建并运行 WebSocket 服务器线程。
        """
        ws_thread = ThreadController(self.run_websocket_server, "wsbot")
        return ws_thread

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

    def stop(self):
        """
        停止 WebSocket 服务器，关闭所有异步任务和连接。
        """
        if self.alive:
            self.alive = False

            # 关闭 WebSocket 连接
            if glob_instance.ws:
                future = asyncio.run_coroutine_threadsafe(glob_instance.ws.close(), self.loop)
                future.result()  # 等待关闭操作完成

            # 停止事件循环
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except:
                pass

            # 取消所有异步任务
            for task in self.tasks:
                task.cancel()
            logger.info("WebSocket server stopping...")
        else:
            logger.warning("WebSocket server is not running.")


# 全局实例
ws_manager = WebSocketManager()
