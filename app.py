import datetime
import os
import time

from common.log import logger
from core.backend import app
from core.wsbot import ws_manager


class Application:
    def __init__(self):
        self.ws_thread = None
        self.fastapi_thread = None
        self.start_time = None
        self.restart_value = True

    def run(self):
        """
        主函数用于同时运行WebSocket服务器和FastAPI应用。
        它通过多线程来实现两者的同时运行，并在接收到键盘中断时安全地停止这两个服务。
        """
        self.start_time = datetime.datetime.now()

        # 创建并运行WebSocket服务器线程
        self.ws_thread = ws_manager.create_job()
        self.ws_thread.start()

        # 创建并运行FastAPI应用线程
        self.fastapi_thread = app.create_job()
        self.fastapi_thread.start()

        # 等待键盘中断
        try:
            while True:
                self.restart()
                time.sleep(2)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        停止所有服务并清理资源。
        """
        end_time = datetime.datetime.now()
        time_difference = end_time - self.start_time
        logger.info(f"本次程序运行了{time_difference},正在停止所有进程...")

        # TODO 这里应该检查是否所有任务都已完成（如图像生成等）
        self.ws_thread.stop()  # 等待WebSocket服务器线程结束，超时5秒
        self.fastapi_thread.stop()  # 等待FastAPI应用线程结束，超时5秒
        logger.info("已停止")

    def restart(self):
        if os.path.exists("restart_info.txt") and self.restart_value:
            with open("restart_info.txt", "r") as f:  # 打开文件
                data = f.read().split(",")  # 读取文件
                if data[0] == "True":
                    self.restart_value = False

                    logger.info("正在重启服务...")
                    ws_manager.stop()  # 停止消息接收
                    self.ws_thread.stop()  # 等待FastAPI应用线程结束

                    self.ws_thread.start()

                    logger.info("服务已重启")
                    os.remove("restart_info.txt")
                    self.restart_value = True


main = Application()
main.run()
