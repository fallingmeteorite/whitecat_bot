import datetime
import os
import time
from typing import Optional

from common import logger
from config import config
from memory_management import simple_memory_release_decorator
from thread_creation import ThreadController


class Application:
    """
    应用程序类，负责管理 WebSocket 服务器和 FastAPI 应用的启动、停止和重启。
    """

    def __init__(self) -> None:
        """
        初始化应用程序。
        """
        self.ws_thread: Optional[ThreadController] = None
        self.start_time: Optional[datetime.datetime] = None
        self.restart_value = True

    def check_py_files(self) -> bool:
        """
        检查适配器目录下是否存在可用的 Python 文件。

        :return: 如果存在有效的适配器文件返回 True，否则返回 False。
        """
        return len(os.listdir(config["adapter_dir"])) > 2

    def run(self) -> None:
        """
        主函数用于同时运行 WebSocket 服务器和 FastAPI 应用。
        它通过多线程来实现两者的同时运行，并在接收到键盘中断时安全地停止这两个服务。
        """
        if not self.check_py_files():
            raise Exception("文件夹内没有可用适配器, 进程退出")

        self.start_time = datetime.datetime.now()

        # 创建并运行 WebSocket 服务器线程
        self.ws_thread = ThreadController("python -m core.message_accept").run()
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

        # 显式删除不再使用的变量
        del self.start_time
        del self.ws_thread

    @simple_memory_release_decorator
    def restart(self) -> None:
        """
        重启 WebSocket 服务器和 FastAPI 应用。
        """
        if self.should_restart("restart.txt"):
            self.restart_service()
            os.remove("restart.txt")
        elif self.should_restart("restart_ignore.txt"):
            self.restart_service()
            os.remove("restart_ignore.txt")

    def should_restart(self, filename: str) -> bool:
        """
        检查是否需要重启服务。

        :param filename: 检查的文件名。
        :return: 如果文件存在并且重启标志为真，则返回 True。
        """
        return os.path.exists(filename) and self.restart_value

    def restart_service(self) -> None:
        """
        执行重启服务逻辑。
        """
        self.restart_value = False

        # 发出重启指令
        open('restart_wsbot.txt', 'w').close()

        while True:
            time.sleep(1.0)
            if not os.path.exists("restart_wsbot.txt"):
                # 创建并运行 WebSocket 服务器线程
                self.ws_thread = ThreadController("python -m core.message_accept").run()
                self.ws_thread.start()
                break

        self.restart_value = True


# 实例化并运行应用程序
main = Application()
main.run()
