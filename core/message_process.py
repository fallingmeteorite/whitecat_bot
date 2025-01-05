import queue
import threading
from typing import Dict, Optional

from common.config import config
from common.logging import logger
from manager.adapter_manager import adapter_manager
from manager.file_manager import file_manager
from manager.filter_manager import filter_manager
from manager.plugin_manager import plugin_manager
from manager.system_manager import system_manager
from utils.block_manager import ban_filter, ban_plugin


class MessageProcessor:
    pause_message_processing = True  # 控制是否暂停消息处理

    def __init__(self):
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()  # 改为使用线程锁
        self.stop_event = threading.Event()  # 控制线程停止的事件

    def add_message(self, websocket, message: Dict) -> None:
        """
        添加消息到队列中。

        Args:
            websocket: WebSocket 连接对象。
            message: 接收到的消息字典。
        """
        uid, nickname, gid, message_dict = adapter_manager.handle_command(message)
        if uid is not None and nickname is not None and message_dict is not None:
            logger.info(f"收到服务器有效数据: {uid}, {nickname}, {gid}, {message_dict}")
            self.message_queue.put((websocket, uid, nickname, gid, message_dict))

            with self.lock:  # 加锁
                if not self.lock.locked():
                    threading.Thread(target=self._process_messages, daemon=True).start()

    def _process_messages(self) -> None:
        """
        处理消息队列中的消息。
        """
        while not self.stop_event.is_set():
            try:
                item = self.message_queue.get(timeout=0.1)
                if self.pause_message_processing:
                    self._process_plugins(item)
                    self._process_files(item)
                    self._process_system(item)
                    self._process_filters(item)
                self.message_queue.task_done()
                item = None  # 显示解除对 item 的引用
            except queue.Empty:
                continue

    def _find_plugin_by_command(self, command: str, plugin_commands: dict) -> Optional[str]:
        """
        根据命令查找插件名称。

        Args:
            command: 用户输入的命令。

        Returns:
            Optional[str]: 插件名称，如果未找到则返回 None。
        """
        for plugin_name, plugin_info in plugin_commands.items():
            if command in plugin_info[2]:
                return plugin_name
        return None

    def _process_plugins(self, item) -> None:
        """
        处理插件消息。
        """
        if not item: return
        websocket, uid, nickname, gid, message_dict = item
        if message_dict['message']['type'] == 'text':
            tmp_message = "".join(message_dict['message']['data']['text'])
            if tmp_message:
                command, *args = tmp_message.split()
                plugin_name = self._find_plugin_by_command(command, plugin_manager.plugin_info)
                if ban_plugin(uid, gid, plugin_name) and plugin_name is not None:
                    logger.debug("功能调用触发")
                    plugin_manager.handle_command(websocket, uid, gid, nickname, message_dict, plugin_name)

    def _process_files(self, item) -> None:
        """
        处理文件消息。
        """
        if not item: return
        websocket, uid, nickname, gid, message_dict = item
        if uid in config['admin'] and "file" in message_dict["message"]["data"]:
            file_name = message_dict["message"]["data"]["file"]
            if file_name in file_manager.file_info:
                logger.debug("本地文件更新触发")
                file_manager.handle_command(websocket, uid, gid, nickname, message_dict, file_name)

    def _process_system(self, item) -> None:
        """
        处理系统消息。
        """
        if not item: return
        websocket, uid, nickname, gid, message_dict = item
        if uid in config["admin"]:
            if message_dict['message']['type'] == 'text':
                tmp_message = "".join(message_dict['message']['data']['text'])
                if tmp_message:
                    command, *args = tmp_message.split()
                    system_name = self._find_plugin_by_command(command, system_manager.system_info)
                    if system_name is not None:
                        logger.debug("系统功能调用触发")
                        system_manager.handle_command(websocket, uid, gid, nickname, message_dict, system_name)

    def _process_filters(self, item) -> None:
        """
        处理过滤器消息。
        """
        if not item: return
        websocket, uid, nickname, gid, message_dict = item
        for filter_name, filter_rule in filter_manager.filter_info.items():
            if ban_filter(uid, gid, filter_name):
                if filter_rule[0] == message_dict['message']["type"]:
                    logger.debug("过滤器触发")
                    filter_manager.handle_message(websocket, uid, gid, message_dict,
                                                  message_dict['message'], filter_name)

    def stop(self) -> None:
        """
        停止消息处理线程。
        """
        self.stop_event.set()


# 全局消息处理器实例
message_processor = MessageProcessor()
