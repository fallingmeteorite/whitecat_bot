from common.log import logger
from common.config import config
from common.module_load import load
from scheduling.thread_scheduling import add_task


class TimerManager:
    def __init__(self):
        self.tasks = []

    def handle_command(self, websocket, gid):
        # 全部异步处理
        asynchronous = True
        for tasks in self.tasks:
            #设置进程id为timer,防止因为超时被杀死
            add_task("timer", tasks[1], asynchronous, websocket, gid, tasks[2])

    # 注册定时器的方法
    def register_timer(self, timer_name, job_func, target_time):
        self.tasks.append([timer_name, job_func, target_time])
        logger.debug(f"TIME| 定时器:{timer_name}加载成功 |TIME")


timer_dir = config["timer_dir"]
timer_manager = load(timer_dir, TimerManager)
