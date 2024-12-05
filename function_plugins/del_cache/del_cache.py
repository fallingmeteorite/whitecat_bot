import os

from common.message_send import send_message
from common.config import config

PLUGIN_NAME = "缓存删除"  # 自定义插件名称


# 删除文件函数
def del_file(folder_path: str):
    # 遍历文件夹中的所有文件
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # 删除文件
                os.remove(file_path)
            except:
                pass


def show_file(folder_path: str):
    total_size = 0
    # 遍历文件夹中的所有文件
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # 获取文件大小并累加
                file_size = os.path.getsize(file_path)
                total_size += file_size
            except:
                pass
    return int(total_size / (1024 * 1024))


def del_cache(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """

    message = message_dict['raw_message']

    if "help" in message:
        show_help(websocket, uid, gid)
        return

    administrator = config["admin"]
    if uid in administrator:
        if "del" in message:
            send_message(websocket, uid, gid, message=f"缓存文件夹清理完成")

        if "show" in message:
            file_size = 0
            folder_path_list = ["log"]
            for folder_path in folder_path_list:
                file_size += show_file(folder_path)
            send_message(websocket, uid, gid, message=f"缓存文件夹大小<{file_size}MB>")


    else:
        send_message(websocket, uid, gid, message="你没有权限执行这条命令!")


def show_help(websocket, uid, gid):
    """
    显示插件的帮助信息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    """
    help_text = ("参数:\n"
                 "del    #删除所有缓存文件\n"
                 "show    #展示文件夹大小")

    send_message(websocket, uid, gid, message=help_text)


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_plugin(
        name=PLUGIN_NAME,
        commands=["del_cache1"],
        asynchronous=False,
        handler=lambda websocket, uid, nickname, gid, message_dict: del_cache(websocket, uid, nickname, gid,
                                                                              message_dict),
    )
