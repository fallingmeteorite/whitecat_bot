from typing import Dict

from common.message_send import send_message

SYSTEM_NAME = "接收控制"  # 自定义插件名称


def accept_control(websocket, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理任务队列信息的显示。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        nickname: 用户昵称。
        gid: 群组 ID。
        message_dict: 消息字典，包含发送的消息。
    """
    from common.message_process import MessageProcessor

    if "help" in message_dict:
        show_help(websocket, uid, gid)
        return

    if "stop" in message_dict["raw_message"]:
        MessageProcessor.pause_message_processing = False
        send_message(websocket, uid, gid, message="停止信息接受")

    if "start" in message_dict["raw_message"]:
        MessageProcessor.pause_message_processing = True
        send_message(websocket, uid, gid, message="开始信息接受")


def show_help(websocket, uid: str, gid: str) -> None:
    """
    显示插件的帮助信息。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID。
    """
    help_text = ("用法:\n"
                 "进程信息 \n"
                 "此命令会返回任务队列。")
    send_message(websocket, uid, gid, message=help_text)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    Args:
        system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/处理"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: accept_control(websocket, uid, nickname, gid,
                                                                                   message_dict),
    )
