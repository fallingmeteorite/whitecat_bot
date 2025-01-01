import asyncio
import time
from typing import Callable, List, Tuple

from common.config import config
from common.logging import logger
from module_manager.plugins_load import load
from scheduling.thread_scheduling import add_task


class TimerManager:
    __slots__ = ['time_tasks']
    """
    定时器管理器类，负责管理定时任务的注册和执行。
    """

    def __init__(self):
        """
        初始化定时器管理器，创建核心列表 `time_tasks` 用于存储定时任务。
        """
        self.time_tasks: List[Tuple[str, Callable, str]] = []

    def handle_command(self, websocket, gid: int) -> None:
        """
        处理定时任务，启动定时器并执行任务。

        Args:
            websocket: WebSocket 连接对象。
            gid: 群组 ID。
        """
        asynchronous = True  # 全部异步处理
        while True:
            if self.time_tasks:
                timer_name, job_func, target_time = self.time_tasks[0]
                # 防止因为超时被杀死
                add_task(False, timer_name, job_func, asynchronous, websocket, gid, target_time)
                logger.debug(f"TIME | 定时器: {timer_name} 启动成功 | TIME")
                del self.time_tasks[0]
            else:
                time.sleep(10.0)  # 没有任务时休眠 10 秒

    def register_plugin(self, timer_name: str, job_func: Callable, target_time: str) -> None:
        """
        注册一个新的定时任务。

        Args:
            timer_name: 定时器名称。
            job_func: 定时任务处理函数。
            target_time: 目标时间。

        Raises:
            ValueError: 如果 `job_func` 不是可调用对象。
        """
        if not callable(job_func):
            raise ValueError("Handler must be a callable function.")
        self.time_tasks.append((timer_name, job_func, target_time))
        logger.debug(f"TIME 定时器:| {timer_name} |加载成功 TIME")


# 加载定时器管理器
timer_dir = config["timer_dir"]
timer_manager, load_module = load(timer_dir, TimerManager)

# 判断是否开启插件热加载
enable_hot_loading = config.get("enable_hot_loading", False)
if enable_hot_loading:
    from module_manager.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(timer_dir, load_module, timer_manager))
    del load_module
