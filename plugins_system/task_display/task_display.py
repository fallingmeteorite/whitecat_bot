import time
from typing import Dict, Any

from common.message_send import send_message
from task_scheduling import get_all_queue_info

SYSTEM_NAME = "任务显示"  # 自定义插件名称


def send_notification(websocket: Any, uid: str, gid: str, message: str) -> None:
    """
    发送通知消息到指定用户或群组。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param gid: 群组 ID。
    :param message: 要发送的消息。
    """
    send_message(websocket, uid, gid, message=message)

def task_display(websocket: Any, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理任务队列信息的显示。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param message_dict: 消息字典，包含发送的消息。
    """

    info = get_all_queue_info("line")
    info += get_all_queue_info("asyncio")
    send_notification(websocket, uid, gid, message=info)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    :param system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/进程信息"],
        timeout_processing=True,
        handler=task_display
    )
