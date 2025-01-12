from typing import Dict, Any

from common.message_send import send_message

SYSTEM_NAME = "接收控制"  # 自定义插件名称


def accept_control(websocket: Any, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理任务队列信息的显示。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    from core.message_process import MessageProcessor

    if "stop" in message_dict["raw_message"]:
        MessageProcessor.pause_message_processing = False
        send_message(websocket, uid, gid, message="停止信息接受")

    if "start" in message_dict["raw_message"]:
        MessageProcessor.pause_message_processing = True
        send_message(websocket, uid, gid, message="开始信息接受")


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    :param system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/消息处理"],
        asynchronous=False,
        timeout_processing=True,
        handler=accept_control
    )
