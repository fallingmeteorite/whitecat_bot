import time

from common.config import config
from common.message_send import send_message
from scheduling.asyn_task_assignment import asyntask
from scheduling.line_task_assignment import linetask

PLUGIN_NAME = "任务显示"  # 自定义插件名称

def format_task_info(task_id, details, max_display_time):
    """格式化任务信息"""
    start_time = details.get("start_time", 0)
    end_time = details.get("end_time", 0)
    status = details.get("status", "unknown")
    continue_timing = details.get("continue_timing", True)

    if continue_timing:
        elapsed_time = end_time - start_time if end_time else time.time() - start_time

        # 如果运行时间超过阈值，停止计时并显示 NAN
        if elapsed_time > max_display_time:
            elapsed_time_display = "NAN"
            details["continue_timing"] = False  # 停止计时
        else:
            elapsed_time_display = f"{elapsed_time:.2f}"
    else:
        elapsed_time_display = "NAN"

    # 根据状态添加特殊提示
    if status == "timeout":
        status_hint = " (任务超时)"
    elif status == "failed":
        status_hint = " (任务失败)"
    else:
        status_hint = ""

    return f"ID: {task_id}, 进程状态: {status}{status_hint}, 已运行时间: {elapsed_time_display} 秒\n"

def get_queue_info_string(task_queue, task_details, max_display_time, queue_type):
    """获取队列信息的字符串"""
    info = ""
    queue_info = task_queue.get_queue_info()
    info += (f"{queue_type}队列数量: {queue_info['queue_size']}, 正在运行的任务数量: {queue_info['running_tasks_count']}\n")

    for task_id, details in queue_info['task_details'].items():
        info += format_task_info(task_id, details, max_display_time)

    return info

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

    # 获取线性队列信息
    info = get_queue_info_string(linetask, linetask.task_details, max_display_time=1000, queue_type="线性")

    # 获取异步队列信息
    info += get_queue_info_string(asyntask, asyntask.task_details, max_display_time=1000, queue_type="异步")

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
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: del_cache(websocket, uid, nickname, gid,
                                                                              message_dict),
    )
