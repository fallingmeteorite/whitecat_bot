import asyncio

from common.config import config
from common.log import logger
from common.module_load import load
from scheduling.thread_scheduling import add_task


class FilterManager:
    def __init__(self):
        self.filter_info = {}

    def register_plugin(self, filter_name, filter_rule, asynchronous, timeout_processing, handler):
        """
        注册一个新的过滤器。
        :param filter_name: 过滤器名称
        :param filter_rule: 过滤器筛选类型。
        :param handler: 处理函数。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        if not isinstance(filter_rule, str):
            raise ValueError("Filter rule must be a string representing a regex pattern.")
        self.filter_info[filter_name] = (filter_rule, asynchronous, timeout_processing, handler)
        logger.debug(f"FILTERS |过滤器:{filter_name}导入成功| FILTERS")

    def handle_message(self, websocket, uid, gid, message_dict, message, filter_name):
        """
        根据已注册的过滤器处理消息。

        :param message: 接收到的消息。
        :param uid: 用户ID。
        :param gid: 群组ID。
        :param websocket: WebSocket连接对象。
        """
        _, asynchronous, timeout_processing, handler = self.filter_info[filter_name]
        add_task(timeout_processing, filter_name, handler, asynchronous, websocket, uid, gid, message, message_dict)


filter_dir = config["filters_dir"]
filter_manager, load_module = load(filter_dir, FilterManager)

# 判断开不开启插件热加载
enable_hot_loading = config["enable_hot_loading"]
if enable_hot_loading:
    from common.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(filter_dir, load_module, filter_manager))
