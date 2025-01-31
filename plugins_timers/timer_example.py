import asyncio
from datetime import datetime, timedelta, time
from typing import Any, List

from message_action import send_message  # 导入发送消息的函数


def main(websocket: Any, gid_all: List[str]) -> None:
    """
    执行主要任务，向每个群组发送消息。

    :param websocket: WebSocket 连接对象。
    :param gid_all: 群组 ID 列表。
    """
    for gid in gid_all:
        send_message(websocket, None, gid, message="")  # 可以自定义消息内容


async def timer(websocket: Any, gid: str, target_time: time) -> None:
    """
    定时器任务，定时向指定群组发送消息。

    :param websocket: WebSocket 连接对象。
    :param gid: 群组 ID。
    :param target_time: 目标时间，定时发送消息的时间点。
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
        main(websocket, [gid])  # 调用 main 函数，传入群组 ID 列表


def register(timer_manager: Any) -> None:
    """
    注册定时器到定时器管理器。

    :param timer_manager: 定时器管理器实例。
    """

    timer_manager.register_timer(
        timer_name="定时器测试",
        # 定义目标时间 15:00
        target_time=time(15, 0),
        handler=timer
    )
