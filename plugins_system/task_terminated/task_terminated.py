import re
from typing import Dict, Any, Optional
from common.message_send import send_message
from task_scheduling import asyntask, linetask

SYSTEM_NAME = "任务终止"  # 自定义插件名称


def parse_plugin_info(message: str) -> Optional[str]:
    """
    解析插件类型和插件名称。

    :param message: 用户输入的消息。
    :return: 插件名称，如果解析失败则返回 None。
    """
    try:
        # 使用正则表达式匹配 | 之间的内容
        plugin_name = re.findall(r'\|([^|]+)\|', message)[0]
        return plugin_name
    except IndexError:
        return None


def task_terminated(websocket: Any, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理任务队列信息的显示。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param message_dict: 消息字典，包含发送的消息。
    """

    message = message_dict["raw_message"].strip()
    plugin_id = parse_plugin_info(message)
    asyntask.force_stop_task(plugin_id)
    linetask.force_stop_task(plugin_id)
    send_message(websocket, None, gid, message="任务结束成功")


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    :param system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/终止"],
        timeout_processing=True,
        handler=task_terminated
    )
