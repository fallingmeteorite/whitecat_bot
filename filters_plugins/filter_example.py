from common.message_send import send_message


def example_filter_function(websocket, uid, gid, message_match, message_dict):
    """
    示例过滤器函数。
    
    :param websocket: WebSocket连接对象。
    :param message_dict: 完整的聊天数据
    """

    if 'hello' in message_match:
        message = f"Matched '{message_match}'"
        send_message(websocket, uid, gid, message=message)
        return True
    return False


def register(filter_manager):
    """
    注册过滤器到FilterManager。
    
    """
    filter_name = "FilterExample"
    filter_rule = "text"
    asynchronous = False,  # 如果你的插件是异步运行则改为True
    timeout_processing = True,
    filter_manager.register_filter(filter_name, filter_rule, asynchronous, timeout_processing, example_filter_function)
