import asyncio
from typing import Callable, Dict, List, Tuple

from common.config import config
from common.logging import logger
from common.message_send import send_message
from utils.module_manager.module_load import load
from scheduling.thread_scheduling import add_task
from utils.user_manager import tracker


class PluginManager:
    __slots__ = ['plugin_info']
    """
    插件管理器类，负责管理插件的注册和命令处理。
    """

    def __init__(self):
        """
        初始化插件管理器，创建核心字典 `plugin_info` 用于存储插件信息。
        """
        self.plugin_info: Dict[str, Tuple[bool, bool, List[str], Callable]] = {}

    def register_plugin(self, name: str, asynchronous: bool, timeout_processing: bool, commands: List[str],
                        handler: Callable) -> None:
        """
        注册一个新的插件。

        Args:
            name: 插件名称。
            asynchronous: 是否异步处理。
            timeout_processing: 是否启用超时处理。
            commands: 插件支持的命令列表。
            handler: 处理函数。

        Raises:
            ValueError: 如果 `handler` 不是可调用对象。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.plugin_info[name] = (asynchronous, timeout_processing, commands, handler)
        logger.debug(f"FUNC 功能插件:| {name} |导入成功 FUNC")

    def handle_command(self, websocket, uid: int, gid: int, nickname: str, message: str, plugin_name: str) -> None:
        """
        根据已注册的插件处理命令。

        Args:
            websocket: WebSocket 连接对象。
            uid: 用户 ID。
            gid: 群组 ID。
            nickname: 用户昵称。
            message: 接收到的消息。
            plugin_name: 插件名称。
        """
        if tracker.use_detections(uid, gid):
            asynchronous, timeout_processing, _, handler = self.plugin_info[plugin_name]
            add_task(
                timeout_processing,
                plugin_name,
                handler,
                asynchronous,
                websocket,
                uid,
                nickname,
                gid,
                message
            )
        else:
            send_message(websocket, None, gid, message="今天你的使用次数到达上限了，休息一会吧")


# 加载插件管理器
plugin_dir = config["plugin_dir"]
plugin_manager, load_module = load(plugin_dir, PluginManager)

# 判断是否开启插件热加载
enable_hot_loading = config.get("enable_hot_loading", False)
if enable_hot_loading:
    from common.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(plugin_dir, load_module, plugin_manager))
    del load_module
