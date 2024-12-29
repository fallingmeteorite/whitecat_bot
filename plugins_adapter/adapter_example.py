def handle_message(message):

    # 提取数据
    uid = None
    nickname = None
    gid = None
    message_dict = {
        "raw_message": None,
        "message": None,
        'message_id': None
    }

    return uid, nickname, gid, message_dict


def register(adapter_manager) -> None:
    """
        注册到适配管理器。

        Args:
            adapter_manager: 文件管理器实例。
        """
    adapter_manager.register_plugin(
        name="xxx适配器",
        handler=lambda message: handle_message(message),
    )

# 保证message_dict中message格式
# {'type': 'image', 'data': {'file': 'xxx', 'subType': 1, 'url': 'xxx', 'file_size': 'xxx'}}
# {'type': 'text', 'data': {'text': 'xxx'}}
# {'type': 'file', 'data': {'file': 'xxx', 'url': 'xxx', 'file_id': 'xxx', 'path': '', 'file_size': 'xxx'}}
