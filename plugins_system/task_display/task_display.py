import time
from typing import Dict

from common.message_send import send_message
from scheduling.asyn_task_assignment import asyntask
from scheduling.line_task_assignment import linetask

SYSTEM_NAME = "任务显示"  # 自定义插件名称


def send_notification(websocket, uid: str, gid: str, message: str) -> None:
    """
    发送通知消息到指定用户或群组。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID。
        message: 要发送的消息。
    """
    send_message(websocket, uid, gid, message=message)


def format_task_info(task_id: str, details: Dict, max_display_time: float) -> str:
    """
    格式化任务信息。

    Args:
        task_id: 任务 ID。
        details: 任务详细信息。
        max_display_time: 最大显示时间。

    Returns:
        str: 格式化后的任务信息。
    """
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
    status_hint = ""
    if status == "timeout":
        status_hint = " (任务超时)"
    elif status == "failed":
        status_hint = " (任务失败)"

    return f"ID: {task_id}, 进程状态: {status}{status_hint}, 已运行时间: {elapsed_time_display} 秒\n"


def get_queue_info_string(task_queue, max_display_time: float, queue_type: str) -> str:
    """
    获取队列信息的字符串。

    Args:
        task_queue: 任务队列对象。
        max_display_time: 最大显示时间。
        queue_type: 队列类型（如 "线性" 或 "异步"）。

    Returns:
        str: 队列信息的字符串。
    """
    try:
        queue_info = task_queue.get_queue_info()
        info = (
            f"\n{queue_type}队列数量: {queue_info['queue_size']}, "
            f"正在运行的任务数量: {queue_info['running_tasks_count']}\n"
        )

        # 输出任务详细信息
        for task_id, details in queue_info['task_details'].items():
            info += format_task_info(task_id, details, max_display_time)

        # 输出错误日志
        if queue_info.get("error_logs"):
            info += f"\n{queue_type}错误日志:\n"
            for error in queue_info["error_logs"]:
                info += (
                    f"任务ID: {error['task_id']}, 报错时间: {error['error_time']}, "
                    f"错误信息: {error['error_message']}\n"
                )

        return info
    except Exception as e:
        return f"获取 {queue_type} 队列信息时出错，请检查日志。\n"


def get_all_queue_info(max_display_time: float) -> str:
    """
    获取所有队列信息的字符串。

    Args:
        max_display_time: 最大显示时间。

    Returns:
        str: 所有队列信息的字符串。
    """
    info = get_queue_info_string(linetask, max_display_time, queue_type="线性")
    info += get_queue_info_string(asyntask, max_display_time, queue_type="异步")
    return info


def task_display(websocket, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    处理任务队列信息的显示。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        nickname: 用户昵称。
        gid: 群组 ID。
        message_dict: 消息字典，包含发送的消息。
    """
    if "help" in message_dict:
        show_help(websocket, uid, gid)
        return

    info = get_all_queue_info(max_display_time=1000)
    send_notification(websocket, uid, gid, message=info)


def show_help(websocket, uid: str, gid: str) -> None:
    """
    显示插件的帮助信息。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID。
    """
    help_text = ("用法:\n"
                 "进程信息 \n"
                 "此命令会返回任务队列。")
    send_notification(websocket, uid, gid, message=help_text)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    Args:
        system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/进程信息"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: task_display(websocket, uid, nickname, gid,
                                                                                 message_dict),
    )
