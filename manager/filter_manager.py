from common.log import logger
from common.config import config
from common.module_load import load
from scheduling.thread_scheduling import add_task


class FilterManager:
    def __init__(self):
        self.filter_name = []
        self.filters = {}
        self.filters_asynchronous = {}
        self.filters_func = {}

    def register_filter(self, filter_name, filter_rule, asynchronous, handler):
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
        self.filter_name.append(filter_name)
        self.filters[filter_name] = filter_rule
        self.filters_asynchronous[filter_name] = asynchronous
        self.filters_func[filter_name] = handler
        logger.debug(f"FILTERS |过滤器:{filter_name}导入成功| FILTERS")

    def handle_message(self, websocket, uid, gid, message_dict, message, filter_name):
        """
        根据已注册的过滤器处理消息。

        :param message: 接收到的消息。
        :param uid: 用户ID。
        :param gid: 群组ID。
        :param websocket: WebSocket连接对象。
        """
        handler = self.filters_func[filter_name]
        add_task(filter_name, handler, self.filters_asynchronous[filter_name], websocket, uid, gid, message,
                 message_dict)


filter_dir = config["filters_dir"]
filter_manager = load(filter_dir, FilterManager)
