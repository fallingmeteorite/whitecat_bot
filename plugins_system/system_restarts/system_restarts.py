from typing import Dict, Any

from common.message_send import send_message

SYSTEM_NAME = "系统重启"  # 自定义插件名称


def send_notification(websocket: Any, uid: str, gid: str, message: str) -> None:
    """
    发送通知消息到指定用户或群组。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param gid: 群组 ID。
    :param message: 要发送的消息。
    """
    send_message(websocket, uid, gid, message=message)


def write_restart_signal(gid: str) -> None:
    """
    将重启信号写入文件。

    :param gid: 群组 ID。
    """
    with open('restart.txt', 'w') as f:
        f.write(gid)  # 可以记录特定群组 ID，供后续使用


def system_restarts(websocket: Any, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理系统重启逻辑。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    send_notification(websocket, uid, gid, message="所有处理线程开始重启，停止接受消息，请稍等")
    write_restart_signal(gid)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    :param system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/system_reboot"],
        asynchronous=False,
        timeout_processing=True,
        handler=system_restarts
    )
