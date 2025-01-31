from typing import Any
from message_action.message_send import send_message


def example_filter_function(websocket: Any, uid: int, gid: int, message_dict: dict) -> bool:
    """
    示例过滤器函数。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    :param message_dict: 完整的聊天数据。
    :return: 如果匹配成功返回 True，否则返回 False。
    """
    if 'hello' in message_dict:
        message = f"Matched '{message_dict}'"
        send_message(websocket, uid, gid, message=message)
        return True
    return False


def register(filter_manager) -> None:
    """
    注册过滤器到FilterManager。

    :param filter_manager: 过滤器管理器实例，用于注册过滤器。
    """
    filter_manager.register_filter(
        filter_name="FilterExample",
        filter_rule="text",
        asynchronous=False,  # 如果你的插件是异步运行则改为 True
        timeout_processing=True,
        handler=example_filter_function
    )
