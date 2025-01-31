import asyncio
import time
from typing import Callable, List, Tuple, Any

from common import logger
from config import config
from plugin_loading import load
from task_scheduling import add_task


class TimerManager:
    __slots__ = ['time_tasks']
    """
    定时器管理器类，负责管理定时任务的注册和执行。
    """

    def __init__(self) -> None:
        """
        初始化定时器管理器，创建核心列表 `time_tasks` 用于存储定时任务。
        """
        self.time_tasks: List[Tuple[str, Callable, str]] = []

    def handle_command(self, websocket: Any, gid: int) -> None:
        """
        处理定时任务，启动定时器并执行任务。

        :param websocket: WebSocket 连接对象。
        :param gid: 群组 ID。
        """
        asynchronous = True  # 全部异步处理
        while True:
            if self.time_tasks:
                timer_name, job_func, target_time = self.time_tasks[0]
                # 防止因为超时被杀死
                add_task(False, timer_name, job_func, websocket, gid, target_time)
                logger.debug(f"TIME | 定时器: {timer_name} 启动成功 | TIME")
                del self.time_tasks[0]
                # 显式删除不再使用的变量（每次循环后清理，保持清洁的内存）
                del timer_name
                del job_func
                del target_time
            else:
                time.sleep(10.0)  # 没有任务时休眠 10 秒



    def register_timer(self, timer_name: str, handler: Callable, target_time: str) -> None:
        """
        注册一个新的定时任务。

        :param timer_name: 定时器名称。
        :param handler: 定时任务处理函数。
        :param target_time: 目标时间。
        :raises ValueError: 如果 `handler` 不是可调用对象。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.time_tasks.append((timer_name, handler, target_time))
        logger.debug(f"TIME 定时器:| {timer_name} |加载成功 TIME")

        # 显式删除不再使用的变量
        del timer_name
        del handler
        del target_time

# 加载定时器管理器
timer_dir = config["timer_dir"]
timer_manager, load_module = load(timer_dir, TimerManager)

# 判断是否开启插件热加载
enable_hot_loading = config.get("enable_hot_loading", False)
if enable_hot_loading:
    from plugin_loading.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(timer_dir, load_module, timer_manager))
del load_module  # 显式删除不再使用的变量
