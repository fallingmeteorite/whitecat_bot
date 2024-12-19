import asyncio
import os
from datetime import datetime, timedelta, time

from common.config import config
from common.message_send import send_message  # 导入日志模块用于记录日志,导入发送消息的函数


def info_reset(websocket):
    if os.path.exists(config["user_use_file"]):
        os.remove(config["user_use_file"])
    for gid in config["use_restricted_groups"]:
        send_message(websocket, None, gid, message="每日使用次数刷新")


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
            info_reset(websocket)


# timer_name, job_func, target_time
def register(timer_manager):
    """
    注册过滤器到FilterManager。

    """
    timer_name = "次数刷新"
    # 定义目标时间 00:00
    target_time = time(18, 17)
    timer_manager.register_plugin(timer_name, timer, target_time)
