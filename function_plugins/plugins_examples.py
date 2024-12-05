from common import send_message  # 导入日志模块用于记录日志,导入发送消息的函数

PLUGIN_NAME = "测试用echo插件"  # 自定义插件名称


def echo(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容。
    
    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    message_send = message_dict["raw_message"]

    if "help" in message_send[:10]:
        show_help(websocket, uid, gid)
        return

    if "CQ" in message_dict["raw_message"] and uid != 3676072566 and uid != 3027312071:
        send_message(websocket, uid, gid, message="🤡🤡🤡你小子想干什么")
        return

    send_message(websocket, uid, gid, message=message_send)


def show_help(websocket, uid, gid):
    """
    显示插件的帮助信息。
    
    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    """
    help_text = ("用法:\n"
                 "echo <message> 或 学我 <message> \n"
                 "此命令会将提供的消息反馈回来。(CQ码内容不会被输出)")
    send_message(websocket, uid, gid, message=help_text)


def register(plugin_manager):
    """
    注册插件到插件管理器。
    
    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_plugin(
        name=PLUGIN_NAME,
        commands=["echo", "学我"],
        asynchronous=False, # 如果你的插件是异步运行则改为True
        handler=lambda websocket, uid, nickname, gid, message_dict: echo(websocket, uid, nickname, gid, message_dict),
    )
