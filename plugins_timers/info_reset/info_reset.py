import asyncio
import os
from datetime import datetime, timedelta, time
from typing import Any

from common.message_send import send_message  # 导入发送消息的函数
from config.config import config


def info_reset(websocket: Any) -> None:
    """
    重置用户使用信息并发送通知。

    :param websocket: WebSocket 连接对象。
    """
    if os.path.exists(config["user_use_file"]):
        os.remove(config["user_use_file"])

    for gid in config["use_restricted_groups"]:
        send_message(websocket, None, gid, message="每日使用次数刷新")


async def timer(websocket: Any, gid: str, target_time: time) -> None:
    """
    定时检查并重置用户的使用信息。

    :param websocket: WebSocket 连接对象。
    :param gid: 群组 ID。
    :param target_time: 目标时间，重置每日使用次数的时间点。
    """

    # 获取当前日期和时间
    now = datetime.now()
    # 创建目标时间（今天的目标时间）
    target = datetime.combine(now.date(), target_time)

    # 如果当前时间已经过了目标时间，则设置为明天的目标时间
    if now >= target:
        target += timedelta(days=1)

    # 计算从当前时间到目标时间的延迟
    delay = (target - now).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
        info_reset(websocket)


def register(timer_manager: Any) -> None:
    """
    注册定时器到定时器管理器。

    :param timer_manager: 定时器管理器实例。
    """

    timer_manager.register_timer(
        timer_name="次数刷新",
        target_time=time(4, 00),  # 设定每日重置时间为 18:17
        handler=timer
    )
