import threading
from typing import Callable, Optional

from common.logging import logger


class ResettableTimer:
    def __init__(self, interval: int, callback: Callable):
        """
        初始化计时器。

        :param interval: 倒计时时间（秒）
        :param callback: 倒计时结束后触发的回调函数
        """
        self.interval = interval
        self.callback = callback
        self.timer: Optional[threading.Timer] = None
        self.lock = threading.Lock()

    def start(self):
        """
        启动或重置计时器。
        """
        with self.lock:
            # 如果计时器已经存在，取消当前计时器
            if self.timer:
                self.timer.cancel()

            # 创建新的计时器
            self.timer = threading.Timer(self.interval, self._on_timeout)
            self.timer.start()

    def _on_timeout(self):
        """
        计时器超时后触发的内部方法。
        """
        if self.callback:
            self.callback()

    def stop(self):
        """
        停止计时器。
        """
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None

# 示例回调函数
def on_timer_end():
    logger.warning("倒计时结束，执行回调函数！")
    with open('restart_ignore.txt', 'w') as f:
        pass

# 初始化计时器（10分钟）
timer = ResettableTimer(interval=600, callback=on_timer_end)

# 触发计时器的函数
def trigger_timer():
    logger.info("触发计时器，重置倒计时！")
    timer.start()
