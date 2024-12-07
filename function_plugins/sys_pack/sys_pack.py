from common.config import config
from common.log import logger
from common.message_send import send_message, get_directories  # 导入发送消息的函数

PLUGIN_NAME = "插件包情况查询"  # 自定义插件名称


def echo(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    output = ""
    for folder in get_directories(config["plugin_dir"]):
        logger.debug(folder)
        # 构造美观的输出，添加表情符号和猫猫颜文字
        output += (f"🐱{folder}🐱(^_^)~~~\n")

    send_message(websocket, uid, gid, message=output)


def show_help(websocket, uid, gid):
    """
    显示插件的帮助信息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    """
    help_text = ("用法:\n"
                 "系统情况 \n"
                 "此命令会反馈服务已加载器插件")
    send_message(websocket, uid, gid, message=help_text)


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_plugin(
        name=PLUGIN_NAME,
        commands=["服务器包", "插件包情况"],
        asynchronous=False,
        handler=lambda websocket, uid, nickname, gid, message_dict: echo(websocket, uid, nickname, gid,
                                                                         message_dict),
    )
