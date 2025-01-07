from typing import Dict, Any
from weakref import ref

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
    # 使用弱引用避免循环引用导致的内存泄漏
    MessageProcessor = ref(__import__("core.message_process").MessageProcessor)

    if "help" in message_dict:
        show_help(websocket, uid, gid)
        return

    if "stop" in message_dict["raw_message"]:
        processor = MessageProcessor()
        if processor:
            processor.pause_message_processing = False
            send_message(websocket, uid, gid, message="停止信息接受")

    if "start" in message_dict["raw_message"]:
        processor = MessageProcessor()
        if processor:
            processor.pause_message_processing = True
            send_message(websocket, uid, gid, message="开始信息接受")


def show_help(websocket: Any, uid: str, gid: str) -> None:
    """
    显示插件的帮助信息。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param gid: 群组 ID。
    """
    help_text = ("用法:\n"
                 "进程信息 \n"
                 "此命令会返回任务队列。")
    send_message(websocket, uid, gid, message=help_text)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    :param system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/处理"],
        asynchronous=False,
        timeout_processing=True,
        handler=accept_control
    )
