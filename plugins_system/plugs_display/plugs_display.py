from typing import Dict, List

from common.config import config
from common.logging import logger
from common.message_send import send_message
from utils.module_manager.module_load import get_directories

SYSTEM_NAME = "插件展示"  # 自定义插件名称


def plugs_display(websocket, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    回显输入的内容，展示已加载的插件目录。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        nickname: 用户昵称。
        gid: 群组 ID。
        message_dict: 消息字典，包含发送的消息。
    """
    plugin_dir = config.get("plugin_dir", "plugins")  # 获取插件目录，默认值为 "plugins"
    directories: List[str] = get_directories(plugin_dir)

    if not directories:
        output = "🐱 当前没有加载任何插件哦 (｡•́︿•̀｡)"
    else:
        output = "🐱 已加载的插件目录如下：\n"
        for folder in directories:
            logger.debug(f"Found plugin directory: {folder}")
            output += f"🐱 {folder} 🐱(^_^)~~~\n"

    send_message(websocket, uid, gid, message=output)


def show_help(websocket, uid: str, gid: str) -> None:
    """
    显示插件的帮助信息。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID。
    """
    help_text = ("用法:\n"
                 "插件列表 \n"
                 "此命令会反馈已加载的插件目录。")
    send_message(websocket, uid, gid, message=help_text)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    Args:
        system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/插件列表"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: plugs_display(websocket, uid, nickname, gid, message_dict),
    )
