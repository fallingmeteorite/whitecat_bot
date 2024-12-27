import os
import threading
from typing import Optional

from common.logging import logger


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
        self.thread: Optional[threading.Thread] = None
        self.force_stop_event = threading.Event()

    def run(self) -> threading.Thread:
        """
        启动线程并执行命令。

        Returns:
            threading.Thread: 启动的线程对象。
        """
        self.force_stop_event.clear()

        def run_command():
            # 使用 os.system 运行命令
            os.system(self.command)

        self.thread = threading.Thread(target=run_command, daemon=True)
        logger.info("Thread started")
        return self.thread

    def stop(self) -> None:
        """
        停止线程，等待线程结束。如果线程未在指定时间内结束，则强制停止。
        """
        logger.info("Thread stopping...")
        if self.thread is not None:
            self.thread.join(timeout=2)  # 等待线程结束，最多等待2秒
            if self.thread.is_alive():
                logger.warning("Thread did not stop in time, forcing termination")
                self.force_stop()
            else:
                logger.info("Thread stopped and cleaned up")

    def force_stop(self) -> None:
        """
        强制停止线程。
        """
        if self.thread is not None:
            self.force_stop_event.set()
            logger.warning("Force stopping the thread")
            self.thread.join(timeout=2)  # 等待线程结束，最多等待2秒
            if self.thread.is_alive():
                logger.error("Thread could not be force stopped")
            else:
                logger.info("Thread force stopped and cleaned up")
