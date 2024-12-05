import asyncio
from datetime import datetime, timedelta, time

from common import send_message  # 导入日志模块用于记录日志,导入发送消息的函数


def main(websocket, gid_all):
    # 你要执行的东西

    for gid in gid_all:
        send_message(websocket, None, gid, message="")


async def timer(websocket, gid, target_time):
    while True:
        # 获取当前日期和时间
        now = datetime.now()
        # 创建目标时间（今天 15:00）
        target = datetime.combine(now.date(), target_time)
        # 如果当前时间已经过了目标时间，则设置为明天的目标时间
        if now >= target:
            target += timedelta(days=1)
        # 计算从当前时间到目标时间的延迟
        delay = (target - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            main(websocket, gid)


# timer_name, job_func, target_time
def register(timer_manager):
    """
    注册过滤器到FilterManager。
    
    """
    timer_name = "定时器测试"
    # 定义目标时间 15:00
    target_time = time(15, 0)
    timer_manager.register_timer(timer_name, timer, target_time)
