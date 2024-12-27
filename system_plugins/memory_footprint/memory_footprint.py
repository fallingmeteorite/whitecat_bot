from typing import Dict

import psutil

from common.message_send import send_message

SYSTEM_NAME = "内存和CPU查询"  # 自定义插件名称


def get_memory_usage() -> str:
    """
    获取内存使用情况并返回格式化字符串。

    Returns:
        str: 内存使用情况的格式化字符串。
    """
    mem = psutil.virtual_memory()
    return (
            "=" * 20 + "\n" +
            "内存使用情况:\n" +
            "=" * 20 + "\n" +
            f"总内存:         {mem.total / (1024 ** 3):.2f} GB\n" +
            f"可用内存:       {mem.available / (1024 ** 3):.2f} GB\n" +
            f"已用内存:       {mem.used / (1024 ** 3):.2f} GB\n" +
            f"内存使用百分比:  {mem.percent} %\n" +
            "=" * 20 + "\n"
    )


def get_top_memory_processes(limit: int = 5) -> str:
    """
    获取内存使用最多的前几个进程并返回格式化字符串。

    Args:
        limit: 返回的进程数量，默认为 5。

    Returns:
        str: 内存使用最多的进程的格式化字符串。
    """
    top_mem = sorted(
        (p for p in psutil.process_iter(['pid', 'name', 'memory_percent']) if p.info['memory_percent'] is not None),
        key=lambda p: p.info['memory_percent'], reverse=True
    )[:limit]

    proc_info = f"内存使用最多的前{limit}个进程:\n"
    for proc in top_mem:
        proc_info += (
            f"PID: {proc.info['pid']} | 名称: {proc.info['name']} | "
            f"内存使用: {proc.info['memory_percent']:.2f}%\n"
        )
    return proc_info


def get_cpu_usage() -> str:
    """
    获取CPU使用情况并返回格式化字符串。

    Returns:
        str: CPU使用情况的格式化字符串。
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    return (
            "=" * 20 + "\n" +
            f"总CPU使用百分比:  {cpu_percent} %\n" +
            "=" * 20 + "\n"
    )


def get_top_cpu_processes(limit: int = 5) -> str:
    """
    获取CPU使用最多的前几个进程并返回格式化字符串。

    Args:
        limit: 返回的进程数量，默认为 5。

    Returns:
        str: CPU使用最多的进程的格式化字符串。
    """
    top_cpu = sorted(
        (p for p in psutil.process_iter(['pid', 'name', 'cpu_percent']) if p.info['cpu_percent'] is not None),
        key=lambda p: p.info['cpu_percent'], reverse=True
    )[:limit]

    proc_info = f"CPU使用最多的前{limit}个进程:\n"
    for proc in top_cpu:
        proc_info += (
            f"PID: {proc.info['pid']} | 名称: {proc.info['name']} | "
            f"CPU使用: {proc.info['cpu_percent']:.2f}%\n"
        )
    return proc_info


def memory_footprint(websocket, uid: str, nickname: str, gid: str, message_dict: Dict) -> None:
    """
    回显输入的内容并发送内存和CPU使用情况。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        nickname: 用户昵称。
        gid: 群组 ID。
        message_dict: 消息字典，包含发送的消息。
    """
    message = message_dict["raw_message"].strip().lower()

    if "help" in message:
        show_help(websocket, uid, gid)
        return

    memory_usage = get_memory_usage()
    top_mem_procs = get_top_memory_processes(5)
    cpu_usage = get_cpu_usage()
    top_cpu_procs = get_top_cpu_processes(5)

    output = memory_usage + top_mem_procs + cpu_usage + top_cpu_procs

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
                 "系统情况 \n"
                 "此命令会反馈服务器内存和CPU信息。")
    send_message(websocket, uid, gid, message=help_text)


def register(system_manager) -> None:
    """
    注册插件到插件管理器。

    Args:
        system_manager: 插件管理器实例。
    """
    system_manager.register_system(
        name=SYSTEM_NAME,
        commands=["/系统情况"],
        asynchronous=False,
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, message_dict: memory_footprint(websocket, uid, nickname, gid,
                                                                                     message_dict),
    )
