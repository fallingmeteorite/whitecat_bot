import os
import re
import shutil

from common.config import config
from common.message_send import send_message

PLUGIN_NAME = "插件管理"  # 自定义插件名称


def enable_set(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """

    if "help" in message_dict["raw_message"]:
        show_help(websocket, uid, gid)
        return None

    if "启用" in message_dict["raw_message"]:
        info = message_dict["raw_message"]
        result = re.findall(r'<(.*?)>', info)[0]
        name = re.findall(r'-(.*?)-', info)[0]

        if result == "定时器":
            path = config["timer_dir"] + f"/{name}"
            if os.path.exists(f"./disuse_plugins/{name}"):
                shutil.move(f"./disuse_plugins/{name}", path)
        if result == "功能":
            path = config["plugin_dir"] + f"/{name}"
            if os.path.exists(f"./disuse_plugins/{name}"):
                shutil.move(f"./disuse_plugins/{name}", path)
        if result == "过滤器":
            path = config["filters_dir"] + f"/{name}"
            if os.path.exists(f"./disuse_plugins/{name}"):
                shutil.move(f"./disuse_plugins/{name}", path)
        if result == "文件接收":
            path = config["file_dir"] + f"/{name}"
            if os.path.exists(f"./disuse_plugins/{name}"):
                shutil.move(f"./disuse_plugins/{name}", path)

        return send_message(websocket, uid, gid, message=f"插件启用成功,启用插件:{result, name}")

    if "禁用" in message_dict["raw_message"]:
        info = message_dict["raw_message"]
        result = re.findall(r'<(.*?)>', info)[0]
        name = re.findall(r'-(.*?)-', info)[0]

        if result == "定时器":
            path = config["timer_dir"] + f"/{name}"
            if os.path.exists(path):
                shutil.move(path, f"./disuse_plugins/{name}")
        if result == "功能":
            path = config["plugin_dir"] + f"/{name}"
            if os.path.exists(path):
                shutil.move(path, f"./disuse_plugins/{name}")
        if result == "过滤器":
            path = config["filters_dir"] + f"/{name}"
            if os.path.exists(path):
                shutil.move(path, f"./disuse_plugins/{name}")
        if result == "文件接收":
            path = config["file_dir"] + f"/{name}"
            if os.path.exists(path):
                shutil.move(path, f"./disuse_plugins/{name}")

        return send_message(websocket, uid, gid, message=f"插件禁用成功,禁用插件:{result, name}")


def show_help(websocket, uid, gid):
    """
    显示插件的帮助信息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    """
    help_text = ("用法:\n"
                 "类型: 定时器,功能,过滤器,文件接收\n"
                 "禁用 <类型>-插件文件夹名字-  \n"
                 "启用 <类型>-插件文件夹名字-  \n"
                 "此命令会移动插件。")
    send_message(websocket, uid, gid, message=help_text)


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_system(
        name=PLUGIN_NAME,
        commands=["插件修改"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: enable_set(websocket, uid, nickname, gid,
                                                                               message_dict),
    )
