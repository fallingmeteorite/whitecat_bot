import os
import threading

from common import logger


class ThreadController:
    """
    线程控制器类，负责管理线程的启动、停止和强制停止。
    """

    def __init__(self, command: str):
        """
        初始化线程控制器。

        Args:
            command: 要执行的命令。
        """
        self.command = command

    def run(self) -> threading.Thread:
        """
        启动线程并执行命令。

        Returns:
            threading.Thread: 启动的线程对象。
        """

        def run_command():
            # 使用 os.system 运行命令
            os.system(self.command)

        thread = threading.Thread(target=run_command, daemon=True)
        logger.info("Thread started")

        # 显式删除不再使用的变量
        del run_command  # 可选，虽然这里是内部函数，但可以清晰地表明它不再被使用

        return thread
