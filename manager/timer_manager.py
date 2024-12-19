from common.config import config
from common.log import logger
from common.module_load import load
from scheduling.thread_scheduling import add_task


class TimerManager:
    def __init__(self):
        self.tasks = []

    def handle_command(self, websocket, gid):
        # 全部异步处理
        asynchronous = True
        for tasks in self.tasks:
            timer_name, job_func, target_time = tasks
            # 设置进程id为timer,防止因为超时被杀死
            add_task(False, timer_name, job_func, asynchronous, websocket, gid, target_time)
            logger.debug(f"TIME| 定时器:{timer_name}启动成功 |TIME")

    # 注册定时器的方法
    def register_timer(self, timer_name, job_func, target_time):
        if not callable(job_func):
            raise ValueError("Handler must be a callable function.")
        self.tasks.append((timer_name, job_func, target_time))
        logger.debug(f"TIME| 定时器:{timer_name}加载成功 |TIME")


timer_dir = config["timer_dir"]
timer_manager = load(timer_dir, TimerManager)
