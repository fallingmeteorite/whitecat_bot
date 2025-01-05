import os
from typing import Dict

from common.config import config
from common.logging import logger
from common.message_send import send_message

SYSTEM_NAME = "缓存删除"  # 自定义插件名称


def del_file(folder_path: str) -> None:
    """
    删除指定文件夹中的所有文件。

    Args:
        folder_path: 文件夹路径。
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件 {file_path} 失败: {e}")


def show_file(folder_path: str) -> int:
    """
    计算指定文件夹中所有文件的总大小（MB）。

    Args:
        folder_path: 文件夹路径。

    Returns:
        int: 文件夹总大小（MB）。
    """
    total_size = 0
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                total_size += os.path.getsize(file_path)
            except Exception as e:
                logger.error(f"获取文件大小 {file_path} 失败: {e}")
    return int(total_size / (1024 * 1024))


def del_cache(websocket, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理缓存删除和展示文件夹大小的命令。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        nickname: 用户昵称。
        gid: 群组 ID。
        message_dict: 消息字典，包含发送的消息。
    """
    message = message_dict['raw_message'].strip().lower()

    if "help" in message:
        show_help(websocket, uid, gid)
        return

    administrator = config.get("admin", [])
    if uid not in administrator:
        send_message(websocket, uid, gid, message="你没有权限执行这条命令!")
        return

    folder_path_list = ["log"]

    if "temp" in message:
        for folder_path in folder_path_list:
            del_file(folder_path)
        send_message(websocket, uid, gid, message="缓存文件夹清理完成")

    elif "show" in message:
        total_size = sum(show_file(folder_path) for folder_path in folder_path_list)
        send_message(websocket, uid, gid, message=f"缓存文件夹大小: {total_size} MB")

    else:
        send_message(websocket, uid, gid, message="无效的命令参数。请使用 'help' 查看帮助。")


def show_help(websocket, uid: str, gid: str) -> None:
    """
    显示插件的帮助信息。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID。
    """
    help_text = ("参数:\n"
                 "temp    # 删除所有缓存文件\n"
                 "show   # 展示文件夹大小")
    send_message(websocket, uid, gid, message=help_text)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    Args:
        system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/del_cache"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: del_cache(websocket, uid, nickname, gid,
                                                                              message_dict),
    )
