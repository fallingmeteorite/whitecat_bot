import time

from common.config import config
from common.message_send import send_message
from scheduling.asyn_task_assignment import asyntask
from scheduling.line_task_assignment import linetask

PLUGIN_NAME = "任务显示"  # 自定义插件名称


def del_cache(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """

    if not uid in config["admin"]:
        return

    info = ""
    queue_info = linetask.get_queue_info()
    info += (f"线性队列数量: {queue_info['queue_size']}, 正在运行的任务数量: {queue_info['running_tasks_count']}\n")

    for task_id, details in queue_info['task_details'].items():
        start_time = details.get("start_time", 0)
        end_time = details.get("end_time", 0)
        status = details.get("status", "unknown")
        elapsed_time = end_time - start_time if end_time else time.time() - start_time
        info += (f"ID: {task_id}, 进程状态: {status}, 已运行时间: {elapsed_time:.2f} 秒\n")

    queue_info = asyntask.get_queue_info()
    info += (f"异步队列数量: {queue_info['queue_size']}, 正在运行的任务数量: {queue_info['running_tasks_count']}\n")

    for task_id, details in queue_info['task_details'].items():
        start_time = details.get("start_time", 0)
        end_time = details.get("end_time", 0)
        status = details.get("status", "unknown")
        elapsed_time = end_time - start_time if end_time else time.time() - start_time
        # 如果运行时间超过阈值，停止计时并显示 NAN
        if elapsed_time > 1000:
            elapsed_time_display = "NAN"
            details["continue_timing"] = False  # 停止计时
        else:
            elapsed_time_display = f"{elapsed_time:.2f} 秒"
        info += (f"ID: {task_id}, 进程状态: {status}, 已运行时间: {elapsed_time_display} 秒\n")

    return send_message(websocket, uid, gid, message=info)


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_plugin(
        name=PLUGIN_NAME,
        commands=["进程信息"],
        asynchronous=False,
        handler=lambda websocket, uid, nickname, gid, message_dict: del_cache(websocket, uid, nickname, gid,
                                                                              message_dict),
    )
