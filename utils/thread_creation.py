import os
import threading
from common.log import logger

class ThreadController:
    def __init__(self, target_func, func_name, *args, **kwargs):
        self.target_func = target_func
        self.func_name = func_name
        self.args = args
        self.kwargs = kwargs
        self.thread = None
        self.running = False
        self.cleanup_event = threading.Event()
        self.force_stop_event = threading.Event()

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.cleanup_event.clear()
            self.force_stop_event.clear()
            self.thread = threading.Thread(target=self._run, name=self.func_name)
            self.thread.daemon = True
            self.thread.start()
            logger.info(f"Thread started: {self.func_name}")
        else:
            logger.warning(f"Thread is already running: {self.func_name}")

    def _run(self):
        try:
            if self.cleanup_event.is_set():
                self._cleanup()
                return
            if self.force_stop_event.is_set():
                logger.warning(f"Force stopping the thread: {self.func_name}")
                self._force_cleanup()
                return
            self.target_func(*self.args, **self.kwargs)  # 只运行指定的函数
        except Exception as e:
            logger.error(f"Error in {self.func_name}: {e}")
        finally:
            self.running = False
            logger.info(f"Thread stopped: {self.func_name}")

    def stop(self):
        if self.running:
            self.running = False
            self.cleanup_event.set()
            logger.info(f"{self.func_name}: Thread stopping...")
            self._cleanup()  # 确保在正常停止时进行清理
            self.thread.join(timeout=5)  # 等待线程结束，最多等待5秒
            if self.thread.is_alive():
                logger.warning(f"Thread did not stop in time, forcing termination: {self.func_name}")
                self.force_stop()
            else:
                logger.info(f"Thread stopped and cleaned up: {self.func_name}")
        else:
            logger.warning(f"Thread is not running: {self.func_name}")

    def force_stop(self):
        if self.running:
            self.running = False
            self.force_stop_event.set()
            logger.warning(f"Force stopping the thread: {self.func_name}")
            self._force_cleanup()
            self.thread.join(timeout=1)  # 等待线程结束，最多等待1秒
            if self.thread.is_alive():
                logger.error(f"Thread could not be force stopped: {self.func_name}")
            else:
                logger.info(f"Thread force stopped and cleaned up: {self.func_name}")
        else:
            logger.warning(f"Thread is not running: {self.func_name}")

    def _cleanup(self):
        logger.info(f"{self.func_name}: Cleaning up...")
        self.args = ()
        self.kwargs = {}
        logger.info(f"Cleanup complete: {self.func_name}")

    def _force_cleanup(self):
        logger.info(f"{self.func_name}: Force cleaning up...")
        self.args = ()
        self.kwargs = {}
        logger.info(f"Force cleanup complete: {self.func_name}")
