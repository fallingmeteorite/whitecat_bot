from typing import Callable, Dict, List, Tuple, Any

from common import logger
from config import config
from plugin_loading import load
from task_scheduling import add_task


class SystemManager:
    __slots__ = ['system_info']
    """
    系统插件管理器类，负责管理系统插件的注册和命令处理。
    """

    def __init__(self) -> None:
        """
        初始化系统插件管理器，创建核心字典 `system_info` 用于存储系统插件信息。
        """
        self.system_info: Dict[str, Tuple[bool, List[str], Callable]] = {}

    def register_system(self, name: str, timeout_processing: bool,
                        commands: List[str], handler: Callable) -> None:
        """
        注册一个新的系统插件。

        :param name: 系统插件名称。
        :param timeout_processing: 是否启用超时处理。
        :param commands: 插件支持的命令列表。
        :param handler: 处理函数。
        :raises ValueError: 如果 `handler` 不是可调用对象。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.system_info[name] = (timeout_processing, commands, handler)
        logger.debug(f"SYSTEM 系统插件:| {name} |导入成功 SYSTEM")

    def handle_command(self, websocket: Any, uid: int, gid: int, nickname: str,
                       message: str, system_name: str) -> None:
        """
        根据已注册的系统插件处理命令。

        :param websocket: WebSocket 连接对象。
        :param uid: 用户 ID。
        :param gid: 群组 ID。
        :param nickname: 用户昵称。
        :param message: 接收到的消息。
        :param system_name: 系统插件名称。
        """
        timeout_processing, _, handler = self.system_info[system_name]
        add_task(
            timeout_processing,
            system_name,
            handler,
            websocket,
            uid,
            nickname,
            gid,
            message
        )

        # 显式删除不再使用的变量
        del timeout_processing
        del handler


# 加载系统插件管理器
system_dir = config["system_dir"]
system_manager, load_module = load(system_dir, SystemManager)

# 显式删除不再使用的变量
del load_module
