import queue
import threading
import weakref
from typing import Dict, Optional, Tuple, Any

from common.logging import logger
from config.config import config
from permission_check.block_manager import ban_filter, ban_plugin
# 加载所有插件
# 先加载适配器
from plugin_processing.adapter_manager import adapter_manager
# 其他插件加载
from plugin_processing.file_manager import file_manager
from plugin_processing.filter_manager import filter_manager
from plugin_processing.plugin_manager import plugin_manager
# 系统插件
from plugin_processing.system_manager import system_manager


class MessageProcessor:
    pause_message_processing = True  # 控制是否暂停消息处理

    def __init__(self):
        self.lock = False  # 用于判断消息处理线程是否开启
        self.message_queue = queue.Queue()
        self.stop_event = threading.Event()  # 控制线程停止的事件

    def add_message(self, websocket: Any, message: Dict) -> None:
        """
        添加消息到队列中。

        Args:
            websocket: WebSocket 连接对象。
            message: 接收到的消息字典。
        """
        # 使用弱引用存储 WebSocket 对象
        websocket_ref = weakref.ref(websocket)

        uid, nickname, gid, message_dict = adapter_manager.handle_command(message)
        if uid is not None and nickname is not None and message_dict is not None:
            logger.info(f"收到服务器有效数据: {uid}, {nickname}, {gid}, {message_dict}")
            self.message_queue.put((websocket_ref, uid, nickname, gid, message_dict))

        if not self.lock:
            self.lock = True
            threading.Thread(target=self._process_messages, daemon=True).start()

    def _process_messages(self) -> None:
        """
        处理消息队列中的消息。
        """
        while not self.stop_event.is_set():
            try:
                item = self.message_queue.get(timeout=0.1)
                self._process_system(item)  # 处理优先级最高
                if self.pause_message_processing:
                    self._process_plugins(item)
                    self._process_files(item)
                    self._process_filters(item)
                self.message_queue.task_done()
                del item  # 显式删除 item
            except queue.Empty:
                continue

    def _find_plugin_by_command(self, command: str, plugin_commands: Dict[str, Any]) -> Optional[str]:
        """
        根据命令查找插件名称。

        Args:
            command: 用户输入的命令。
            plugin_commands: 插件命令字典。

        Returns:
            Optional[str]: 插件名称，如果未找到则返回 None。
        """
        for plugin_name, plugin_info in plugin_commands.items():
            if command in plugin_info[2]:
                return plugin_name
        return None

    def _process_plugins(self, item: Tuple[weakref.ref, Any, str, str, Dict]) -> None:
        """
        处理插件消息。

        Args:
            item: 包含 WebSocket 弱引用、用户 ID、昵称、群组 ID 和消息字典的元组。
        """
        websocket_ref, uid, nickname, gid, message_dict = item
        websocket = websocket_ref()
        if websocket and message_dict['message']['type'] == 'text':
            tmp_message = "".join(message_dict['message']['data']['text'])
            if tmp_message:
                command, *_ = tmp_message.split()
                plugin_name = self._find_plugin_by_command(command, plugin_manager.plugin_info)
                if plugin_name and ban_plugin(uid, gid, plugin_name):
                    logger.debug("功能调用触发")
                    plugin_manager.handle_command(websocket, uid, gid, nickname, message_dict, plugin_name)
                del command, plugin_name
            del tmp_message
        del websocket_ref, uid, nickname, gid, message_dict, websocket  # 显式删除变量

    def _process_files(self, item: Tuple[weakref.ref, Any, str, str, Dict]) -> None:
        """
        处理文件消息。

        Args:
            item: 包含 WebSocket 弱引用、用户 ID、昵称、群组 ID 和消息字典的元组。
        """
        websocket_ref, uid, nickname, gid, message_dict = item
        websocket = websocket_ref()
        if websocket and uid in config['admin'] and "file" in message_dict["message"]["data"]:
            file_name = message_dict["message"]["data"]["file"]
            if file_name in file_manager.file_info:
                logger.debug("本地文件更新触发")
                file_manager.handle_command(websocket, uid, gid, nickname, message_dict, file_name)
                del file_name
        del websocket_ref, uid, nickname, gid, message_dict, websocket  # 显式删除变量

    def _process_system(self, item: Tuple[weakref.ref, Any, str, str, Dict]) -> None:
        """
        处理系统消息。

        Args:
            item: 包含 WebSocket 弱引用、用户 ID、昵称、群组 ID 和消息字典的元组。
        """
        websocket_ref, uid, nickname, gid, message_dict = item
        websocket = websocket_ref()
        if websocket and uid in config["admin"] and message_dict['message']['type'] == 'text':
            tmp_message = "".join(message_dict['message']['data']['text'])
            if tmp_message:
                command, *_ = tmp_message.split()
                system_name = self._find_plugin_by_command(command, system_manager.system_info)
                if system_name:
                    logger.debug("系统功能调用触发")
                    system_manager.handle_command(websocket, uid, gid, nickname, message_dict, system_name)
                del command, system_name
            del tmp_message
        del websocket_ref, uid, nickname, gid, message_dict, websocket  # 显式删除变量

    def _process_filters(self, item: Tuple[weakref.ref, Any, str, str, Dict]) -> None:
        """
        处理过滤器消息。

        Args:
            item: 包含 WebSocket 弱引用、用户 ID、昵称、群组 ID 和消息字典的元组。
        """
        websocket_ref, uid, nickname, gid, message_dict = item
        websocket = websocket_ref()
        if websocket:
            for filter_name, filter_rule in filter_manager.filter_info.items():
                if ban_filter(uid, gid, filter_name) and filter_rule[0] == message_dict['message']["type"]:
                    logger.debug("过滤器触发")
                    filter_manager.handle_message(websocket, uid, gid, message_dict,
                                                  message_dict['message'], filter_name)
                del filter_name, filter_rule
        del websocket_ref, uid, nickname, gid, message_dict, websocket  # 显式删除变量

    def stop(self) -> None:
        """
        停止消息处理线程。
        """
        self.stop_event.set()


# 全局消息处理器实例
message_processor = MessageProcessor()
