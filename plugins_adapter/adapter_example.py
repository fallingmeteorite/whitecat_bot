from typing import Any, Dict, Tuple, Optional

def handle_message(message: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Optional[int], Dict[str, Any]]:
    """
    处理传入的消息，提取用户 ID、昵称和群组 ID。

    :param message: 原始消息字典。
    :return: 用户 ID、昵称、群组 ID 和消息字典。
    """
    # 提取数据
    uid = None
    nickname = None
    gid = None
    message_dict = {
        "raw_message": message,
        "message": None,
        'message_id': None
    }

    # 这里可以添加逻辑来处理并填充 uid, nickname, gid, message_dict

    return uid, nickname, gid, message_dict


def register(adapter_manager) -> None:
    """
    注册到适配管理器。

    :param adapter_manager: 文件管理器实例，用于注册适配器。
    """
    adapter_manager.register_plugin(
        name="xxx适配器",
        handler=handle_message
    )

# 保证 message_dict 中 message 格式
# {'type': 'image', 'data': {'file': 'xxx', 'subType': 1, 'url': 'xxx', 'file_size': 'xxx'}}
# {'type': 'text', 'data': {'text': 'xxx'}}
# {'type': 'file', 'data': {'file': 'xxx', 'url': 'xxx', 'file_id': 'xxx', 'path': '', 'file_size': 'xxx'}}
