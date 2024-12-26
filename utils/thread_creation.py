import os
import threading

from common.logging import logger


class ThreadController:
    def __init__(self, command):
        self.command = command
        self.thread = None
        self.force_stop_event = threading.Event()

    def run(self):
        self.force_stop_event.clear()

        def run_command():
            # 使用 os.system 运行命令
            os.system(self.command)

        self.thread = threading.Thread(target=run_command, daemon=True)
        logger.info("Thread started")
        return self.thread

    def stop(self):
        logger.info("Thread stopping...")
        self.thread.join(timeout=2)  # 等待线程结束，最多等待2秒
        if self.thread.is_alive():
            logger.warning("Thread did not stop in time, forcing termination")
            self.force_stop()
        else:
            logger.info("Thread stopped and cleaned up")

    def force_stop(self):

        self.force_stop_event.set()
        logger.warning("Force stopping the thread")
        self.thread.join(timeout=2)  # 等待线程结束，最多等待2秒
        if self.thread.is_alive():
            logger.error("Thread could not be force stopped")
        else:
            logger.info("Thread force stopped and cleaned up")
