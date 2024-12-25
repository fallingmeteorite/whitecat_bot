from common.config import config
from common.log import logger
from common.message_send import send_message  # 导入发送消息的函数
from common.module_load import get_directories

PLUGIN_NAME = "插件展示"  # 自定义插件名称


def echo(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容，展示已加载的插件目录。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    plugin_dir = config["plugin_dir"]  # 获取插件目录，默认值为 "plugins"
    directories = get_directories(plugin_dir)

    if not directories:
        output = "🐱 当前没有加载任何插件哦 (｡•́︿•̀｡)"
    else:
        output = "🐱 已加载的插件目录如下：\n"
        for folder in directories:
            logger.debug(f"Found plugin directory: {folder}")
            output += f"🐱 {folder} 🐱(^_^)~~~\n"

    send_message(websocket, uid, gid, message=output)


def show_help(websocket, uid, gid):
    """
    显示插件的帮助信息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    """
    help_text = ("用法:\n"
                 "插件列表 \n"
                 "此命令会反馈已加载的插件目录。")
    send_message(websocket, uid, gid, message=help_text)


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_system(
        name=PLUGIN_NAME,
        commands=["插件列表"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: echo(websocket, uid, nickname, gid, message_dict),
    )
