import asyncio
from typing import Callable, Dict, Tuple, Any

from common.logging import logger
from config.config import config
from plugin_loading.plugins_load import load
from task_scheduling.thread_scheduling import add_task


class FileManager:
    __slots__ = ['file_info']
    """
    文件管理器类，负责管理文件的处理函数和任务调度。
    """

    def __init__(self) -> None:
        """
        初始化文件管理器，创建核心字典 `file_info` 用于存储文件处理函数。
        """
        self.file_info: Dict[str, Tuple[bool, bool, Callable]] = {}

    def register_plugin(self, name: str, asynchronous: bool, timeout_processing: bool, handler: Callable) -> None:
        """
        注册文件处理插件。

        :param name: 文件名称。
        :param asynchronous: 是否异步处理。
        :param timeout_processing: 是否启用超时处理。
        :param handler: 文件处理函数。
        :raises ValueError: 如果 `handler` 不是可调用对象。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.file_info[name] = (asynchronous, timeout_processing, handler)
        logger.debug(f"FILE 文件检测:| {name} |导入成功 FILE")

    def handle_command(self, websocket: Any, uid: int, gid: int, nickname: str, message_dict: dict, file: str) -> None:
        """
        处理文件命令，调度文件处理任务。

        :param websocket: WebSocket 连接对象。
        :param uid: 用户 ID。
        :param gid: 群组 ID。
        :param nickname: 用户昵称。
        :param message_dict: 消息字典。
        :param file: 文件名称。
        """
        # 获取文件处理函数及其配置
        asynchronous, timeout_processing, handler = self.file_info[file]
        # 添加任务到调度器
        add_task(
            timeout_processing,
            file,
            handler,
            asynchronous,
            websocket,
            uid,
            nickname,
            gid,
            message_dict["message"]["data"]["file_id"]
        )


# 加载文件管理器
file_dir = config["file_dir"]
file_manager, load_module = load(file_dir, FileManager)

# 判断是否开启插件热加载
enable_hot_loading = config.get("enable_hot_loading", False)
if enable_hot_loading:
    from plugin_loading.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(file_dir, load_module, file_manager))
    del load_module
