import datetime
import os
import time
from typing import Optional

from common.config import config
from common.logging import logger
from utils.thread_creation import ThreadController


class Application:
    """
    应用程序类，负责管理 WebSocket 服务器和 FastAPI 应用的启动、停止和重启。
    """

    def __init__(self):
        """
        初始化应用程序。
        """
        self.ws_thread: Optional[ThreadController] = None
        self.fastapi_thread: Optional[ThreadController] = None
        self.start_time: Optional[datetime.datetime] = None
        self.restart_value = True

    def check_py_files(self) -> bool:
        """
        检查指定目录下是否存在 .py 文件。

        Args:
            directory: 要检查的目录路径。

        Returns:
            bool: 如果存在 .py 文件返回 True，否则返回 False。
        """
        # 检查路径是否存在
        directory = config["adapter_dir"]
        if not os.path.exists(directory):
            return False

        # 检查路径是否是一个目录
        if not os.path.isdir(directory):
            return False

        # 遍历目录，检查是否存在 .py 文件
        for file in os.listdir(directory):
            if file.endswith(".py"):
                return True

        logger.debug(f"在目录 '{directory}' 中未找到 .py 文件。")
        return False

    def run(self) -> None:
        """
        主函数用于同时运行 WebSocket 服务器和 FastAPI 应用。
        它通过多线程来实现两者的同时运行，并在接收到键盘中断时安全地停止这两个服务。
        """
        if not self.check_py_files():
            raise Exception("文件夹内没有可用适配器,进程退出")

        self.start_time = datetime.datetime.now()

        # 创建并运行 WebSocket 服务器线程
        self.fastapi_thread = ThreadController("python -m core.document_process").run()
        self.ws_thread = ThreadController("python -m core.message_accept").run()

        self.fastapi_thread.start()
        self.ws_thread.start()

        # 等待键盘中断
        try:
            while True:
                self.restart()
                time.sleep(4)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """
        停止所有服务并清理资源。
        """
        end_time = datetime.datetime.now()
        logger.info(f"本次程序运行了 {end_time - self.start_time}, 正在停止所有进程...")
        logger.info("已停止")

    def restart(self) -> None:
        """
        重启 WebSocket 服务器和 FastAPI 应用。
        """
        if os.path.exists("restart.txt") and self.restart_value:
            with open("restart.txt", "r") as f:
                data = f.read().split(",")
            if data[0] == "stop":
                self.start_time = datetime.datetime.now()
                self.restart_value = False
                with open('restart_wsbot.txt', 'w') as f:
                    pass
                with open('restart_fastapi.txt', 'w') as f:
                    pass
                os.remove("restart.txt")
                logger.warning("正在重启服务...")

                while True:
                    time.sleep(1.0)
                    if not os.path.exists("restart_wsbot.txt") and not os.path.exists(
                            "restart_fastapi.txt") and not self.restart_value:
                        self.restart_value = True

                        # 创建并运行 WebSocket 服务器线程
                        self.fastapi_thread = ThreadController("python -m core.document_process").run()
                        self.ws_thread = ThreadController("python -m core.message_accept").run()
                        self.fastapi_thread.start()
                        self.ws_thread.start()

                        end_time = datetime.datetime.now()
                        with open('restart.txt', 'w') as f:
                            f.write(f"ok,{data[1]},{end_time - self.start_time}")
                            break
                logger.info("服务器重启完毕")


main = Application()
main.run()
