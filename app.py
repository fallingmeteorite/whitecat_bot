import datetime
import os
import time

from common.logging import logger
from utils.thread_creation import ThreadController


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
        self.fastapi_thread = ThreadController("python -m core.document_processing").run()
        self.ws_thread = ThreadController("python -m core.message_acceptance").run()

        self.fastapi_thread.start()
        self.ws_thread.start()

        # 等待键盘中断
        try:
            while True:
                self.restart()
                time.sleep(4)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        停止所有服务并清理资源。
        """
        end_time = datetime.datetime.now()
        logger.info(f"本次程序运行了{end_time - self.start_time},正在停止所有进程...")
        logger.info("已停止")

    def restart(self):
        if os.path.exists("restart.txt") and self.restart_value:
            with open("restart.txt", "r") as f:  # 打开文件
                data = f.read().split(",")  # 读取文件
            if data[0] == "stop":
                self.restart_value = False
                with open('restart_wsbot.txt', 'w') as f:
                    f.write("restart")
                with open('restart_fastapi.txt', 'w') as f:
                    f.write("restart")
                os.remove("restart.txt")
                logger.warning("正在重启服务...")
                self.start_time = datetime.datetime.now()
                while True:
                    time.sleep(1.0)
                    if not os.path.exists("restart_wsbot.txt") and not os.path.exists(
                            "restart_wsbot.txt") and not self.restart_value:
                        self.restart_value = True

                        # 创建并运行WebSocket服务器线程
                        self.fastapi_thread = ThreadController("python -m core.document_processing").run()
                        self.ws_thread = ThreadController("python -m core.message_acceptance").run()
                        self.fastapi_thread.start()
                        self.ws_thread.start()

                        end_time = datetime.datetime.now()
                        with open('restart.txt', 'w') as f:
                            f.write(f"ok,{data[1]},{end_time - self.start_time}")
                            break
                logger.info("服务器重启完毕")


main = Application()
main.run()
