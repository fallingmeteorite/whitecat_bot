import os
import re
import shutil
from typing import Dict, Optional, Tuple, Any

from common.message_send import send_message
from config.config import config

SYSTEM_NAME = "插件管理"  # 自定义插件名称


def enable_set(websocket: Any, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理插件的启用和禁用命令。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    message = message_dict["raw_message"].strip()

    if "启用" in message:
        plugin_type, plugin_name = parse_plugin_info(message)
        if plugin_type and plugin_name:
            enable_plugin(plugin_type, plugin_name)
            send_message(websocket, uid, gid, message=f"插件启用成功, 启用插件: {plugin_type}, {plugin_name}")
        else:
            send_message(websocket, uid, gid, message="插件启用失败, 请检查命令格式。")

    elif "禁用" in message:
        plugin_type, plugin_name = parse_plugin_info(message)
        if plugin_type and plugin_name:
            disable_plugin(plugin_type, plugin_name)
            send_message(websocket, uid, gid, message=f"插件禁用成功, 禁用插件: {plugin_type}, {plugin_name}")
        else:
            send_message(websocket, uid, gid, message="插件禁用失败, 请检查命令格式。")

    else:
        send_message(websocket, uid, gid, message="无效的命令参数。请使用 'help' 查看帮助。")


def parse_plugin_info(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析插件类型和插件名称。

    :param message: 用户输入的消息。
    :return: (插件类型, 插件名称)，如果解析失败则返回 (None, None)。
    """
    try:
        plugin_type = re.findall(r'<(.*?)>', message)[0]
        plugin_name = re.findall(r'-(.*?)-', message)[0]
        return plugin_type, plugin_name
    except IndexError:
        return None, None


def enable_plugin(plugin_type: str, plugin_name: str) -> None:
    """
    启用插件。

    :param plugin_type: 插件类型（如 "定时器", "功能", "过滤器", "文件接收"）。
    :param plugin_name: 插件名称。
    """
    plugin_dirs = {
        "定时器": config["timer_dir"],
        "功能": config["plugin_dir"],
        "过滤器": config["filters_dir"],
        "文件接收": config["file_dir"]
    }
    if plugin_type in plugin_dirs:
        source_path = f"./plugins_disuse/{plugin_name}"
        target_path = os.path.join(plugin_dirs[plugin_type], plugin_name)
        if os.path.exists(source_path):
            shutil.move(source_path, target_path)


def disable_plugin(plugin_type: str, plugin_name: str) -> None:
    """
    禁用插件。

    :param plugin_type: 插件类型（如 "定时器", "功能", "过滤器", "文件接收"）。
    :param plugin_name: 插件名称。
    """
    plugin_dirs = {
        "定时器": config["timer_dir"],
        "功能": config["plugin_dir"],
        "过滤器": config["filters_dir"],
        "文件接收": config["file_dir"]
    }
    if plugin_type in plugin_dirs:
        source_path = os.path.join(plugin_dirs[plugin_type], plugin_name)
        target_path = f"./plugins_disuse/{plugin_name}"
        if os.path.exists(source_path):
            shutil.move(source_path, target_path)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    Args:
        system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/插件修改"],
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: enable_set(websocket, uid, nickname, gid,
                                                                               message_dict),
    )
