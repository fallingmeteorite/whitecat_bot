from typing import Dict, Any

from message_action.message_send import send_message

PLUGIN_NAME = "测试用 Echo 插件"  # 自定义插件名称


def send_notification(websocket: Any, uid: str, gid: str, message: str) -> None:
    """
    发送通知消息到指定用户或群组。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param gid: 群组 ID。
    :param message: 要发送的消息。
    """
    send_message(websocket, uid, gid, message=message)


def echo(websocket: Any, uid: str, nickname: str, gid: str, message_dict: Dict[str, Any]) -> None:
    """
    回显输入的内容。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    message_send = message_dict["raw_message"]

    if "help" in message_send:
        show_help(websocket, uid, gid)
        return

    send_notification(websocket, uid, gid, message=message_send)


def show_help(websocket: Any, uid: str, gid: str) -> None:
    """
    显示插件的帮助信息。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param gid: 群组 ID。
    """
    help_text = "用法: 输入任意消息，插件将回显该消息。"
    send_notification(websocket, uid, gid, message=help_text)


def register(plugin_manager) -> None:
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_plugin(
        name=PLUGIN_NAME,
        commands=["echo"],
        asynchronous=False,  # 如果你的插件是异步运行则改为 True
        timeout_processing=True,
        handler=echo
    )
