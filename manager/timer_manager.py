import asyncio
import time

from common.config import config
from common.log import logger
from common.module_load import load
from scheduling.thread_scheduling import add_task


class TimerManager:
    def __init__(self):
        self.time_tasks = []

    def handle_command(self, websocket, gid):
        # 全部异步处理
        asynchronous = True
        while True:
            if not len(self.time_tasks) == 0:
                timer_name, job_func, target_time = self.time_tasks[0]
                # 防止因为超时被杀死
                add_task(False, timer_name, job_func, asynchronous, websocket, gid, target_time)
                logger.debug(f"TIME| 定时器:{timer_name}启动成功 |TIME")
                del self.time_tasks[0]
            else:
                time.sleep(10.0)

    # 注册定时器的方法
    def register_plugin(self, timer_name, job_func, target_time):
        if not callable(job_func):
            raise ValueError("Handler must be a callable function.")
        self.time_tasks.append((timer_name, job_func, target_time))
        logger.debug(f"TIME| 定时器:{timer_name}加载成功 |TIME")


timer_dir = config["timer_dir"]
timer_manager, load_module = load(timer_dir, TimerManager)

# 判断开不开启插件热加载
enable_hot_loading = config["enable_hot_loading"]
if enable_hot_loading:
    from common.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(timer_dir, load_module, timer_manager))
