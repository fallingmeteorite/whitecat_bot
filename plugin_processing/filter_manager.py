import asyncio
from typing import Callable, Dict, Tuple, Any

from common.logging import logger
from config.config import config
from plugin_loading.plugins_load import load
from task_scheduling.thread_scheduling import add_task


class FilterManager:
    __slots__ = ['filter_info']
    """
    过滤器管理器类，负责管理过滤器的注册和消息处理。
    """

    def __init__(self) -> None:
        """
        初始化过滤器管理器，创建核心字典 `filter_info` 用于存储过滤器信息。
        """
        self.filter_info: Dict[str, Tuple[str, bool, bool, Callable]] = {}

    def register_plugin(self, filter_name: str, filter_rule: str, asynchronous: bool, timeout_processing: bool,
                        handler: Callable) -> None:
        """
        注册一个新的过滤器。

        :param filter_name: 过滤器名称。
        :param filter_rule: 过滤器筛选类型（正则表达式字符串）。
        :param asynchronous: 是否异步处理。
        :param timeout_processing: 是否启用超时处理。
        :param handler: 处理函数。
        :raises ValueError: 如果 `handler` 不是可调用对象或 `filter_rule` 不是字符串。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        if not isinstance(filter_rule, str):
            raise ValueError("Filter rule must be a string representing a regex pattern.")
        self.filter_info[filter_name] = (filter_rule, asynchronous, timeout_processing, handler)
        logger.debug(f"FILTERS 过滤器:| {filter_name} |导入成功 FILTERS")

    def handle_message(self, websocket: Any, uid: int, gid: int, message_dict: dict, message: str,
                       filter_name: str) -> None:
        """
        根据已注册的过滤器处理消息。

        :param websocket: WebSocket 连接对象。
        :param uid: 用户 ID。
        :param gid: 群组 ID。
        :param message_dict: 消息字典。
        :param message: 接收到的消息。
        :param filter_name: 过滤器名称。
        """
        filter_rule, asynchronous, timeout_processing, handler = self.filter_info[filter_name]
        add_task(
            timeout_processing,
            filter_name,
            handler,
            asynchronous,
            websocket,
            uid,
            gid,
            message,
            message_dict
        )

        # 显式删除不再使用的变量
        del filter_rule
        del asynchronous
        del timeout_processing
        del handler


# 加载过滤器管理器
filter_dir = config["filters_dir"]
filter_manager, load_module = load(filter_dir, FilterManager)

# 判断是否开启插件热加载
enable_hot_loading = config.get("enable_hot_loading", False)
if enable_hot_loading:
    from plugin_loading.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(filter_dir, load_module, filter_manager))

del load_module # 显式删除不再使用的变量
