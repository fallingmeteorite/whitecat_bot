import psutil
from common.message_send import send_message  # 导入发送消息的函数

PLUGIN_NAME = "内存查询"  # 自定义插件名称


def get_memory_usage():
    """获取内存使用情况并返回格式化字符串"""
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


def get_top_memory_processes(limit=5):
    """获取内存使用最多的前几个进程并返回格式化字符串"""
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


def echo(websocket, uid, nickname, gid, message_dict):
    """
    回显输入的内容并发送内存使用情况。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param nickname: 用户昵称。
    :param gid: 群组ID。
    :param message_dict: 消息字典，包含发送的消息。
    """
    message = message_dict["raw_message"].strip().lower()

    if "help" in message:
        show_help(websocket, uid, gid)
        return

    memory_usage = get_memory_usage()
    top_procs = get_top_memory_processes(5)
    output = memory_usage + top_procs

    send_message(websocket, uid, gid, message=output)


def show_help(websocket, uid, gid):
    """
    显示插件的帮助信息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID。
    """
    help_text = ("用法:\n"
                 "系统情况 \n"
                 "此命令会反馈服务器内存占用情况。")
    send_message(websocket, uid, gid, message=help_text)


def register(plugin_manager):
    """
    注册插件到插件管理器。

    :param plugin_manager: 插件管理器实例。
    """
    plugin_manager.register_plugin(
        name=PLUGIN_NAME,
        commands=["内存情况"],
        asynchronous=False,
        handler=lambda websocket, uid, nickname, gid, message_dict: echo(websocket, uid, nickname, gid, message_dict),
    )