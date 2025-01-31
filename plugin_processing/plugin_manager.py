import asyncio
from typing import Callable, Dict, List, Tuple, Any

from common import logger
from config import config
from message_action import send_message
from permission_check import tracker
from plugin_loading import load
from task_scheduling import add_task


class PluginManager:
    __slots__ = ['plugin_info', 'load_module']
    """
    插件管理器类，负责管理插件的注册和命令处理。
    """

    def __init__(self) -> None:
        """
        初始化插件管理器，创建核心字典 `plugin_info` 用于存储插件信息。
        """
        self.plugin_info: Dict[str, Tuple[bool, List[str], Callable]] = {}
        self.load_module: Dict = {}

    def register_plugin(self, name: str, timeout_processing: bool,
                        commands: List[str], handler: Callable) -> None:
        """
        注册一个新的插件。

        :param name: 插件名称。
        :param timeout_processing: 是否启用超时处理。
        :param commands: 插件支持的命令列表。
        :param handler: 处理函数。
        :raises ValueError: 如果 `handler` 不是可调用对象。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.plugin_info[name] = (timeout_processing, commands, handler)
        logger.debug(f"FUNC 功能插件:| {name} |导入成功 FUNC")

    def handle_command(self, websocket: Any, uid: int, gid: int, nickname: str, message: str, plugin_name: str) -> None:
        """
        根据已注册的插件处理命令。

        :param websocket: WebSocket 连接对象。
        :param uid: 用户 ID。
        :param gid: 群组 ID。
        :param nickname: 用户昵称。
        :param message: 接收到的消息。
        :param plugin_name: 插件名称。
        """
        if tracker.can_use_detection(uid, gid):
            timeout_processing, _, handler = self.plugin_info[plugin_name]
            add_task(
                timeout_processing,
                plugin_name,
                handler,
                websocket,
                uid,
                nickname,
                gid,
                message
            )
        else:
            send_message(websocket, None, gid, message="今天你的使用次数到达上限了，休息一会吧")

        # 显式删除不再使用的变量
        del websocket
        del uid
        del gid
        del nickname
        del message
        del plugin_name


# 加载插件管理器
plugin_dir = config["plugin_dir"]
plugin_manager, load_module = load(plugin_dir, PluginManager)

# 判断是否开启插件热加载
enable_hot_loading = config.get("enable_hot_loading", False)
if enable_hot_loading:
    from plugin_loading.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(plugin_dir, load_module, plugin_manager))
del load_module  # 显式删除不再使用的变量
