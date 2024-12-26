from common.message_send import send_message

PLUGIN_NAME = "系统重启"  # 自定义插件名称


def system_restarts(websocket, uid, nickname, gid, message_dict):
    send_message(websocket, uid, gid, message="所有处理线程开始重启,停止接受消息,请稍等")
    with open('restart.txt', 'w') as f:
        f.write(f"stop,{gid}")


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_system(
        name=PLUGIN_NAME,
        commands=["system_reboot"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: system_restarts(websocket, uid, nickname, gid,
                                                                                    message_dict),
    )
