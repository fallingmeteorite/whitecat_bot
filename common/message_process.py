import os
import queue
import threading
import time

from common.config import config
from common.log import logger
from core.globals import glob_instance
from manager.block_manager import ban_filter, ban_plugin
from manager.file_manager import file_manager
from manager.filter_manager import filter_manager
from manager.plugin_manager import plugin_manager
from manager.system_manager import system_manager
from manager.timer_manager import timer_manager


# 获取命令调用的插件
def find_plugin_by_command(command, plugin_commands):
    for info in plugin_commands.items():
        if command in info[1][2]:
            return info[0]
    return None


class MessageProcess:

    def __init__(self):
        self.message_queue = queue.Queue()
        # 用于判断消息处理线程是否开启
        self.lock = False
        # 当主程序的关闭时,用于关闭消息处理线程
        self.stop_event = threading.Event()  # 用于控制线程停止的事件
        self.pause_message_processing = True  # 用于控制是否暂停消息处理

    # 添加消息到队列中
    def add_message(self, websocket, message):
        uid, nickname, gid, message_dict = self.handle_message(message)
        # 只接受有效数据,无效数据不接受
        if uid is not None or nickname is not None or message_dict is not None:
            logger.info(f"收到服务器有效数据: {uid, nickname, gid, message_dict}\n")
            self.message_queue.put((websocket, uid, nickname, gid, message_dict))

        if not self.lock:
            self.lock = True
            # 开启消息处理线程
            # 不设置守护线程,因为任务调度也在这个线程下面
            threading.Thread(target=self.plugin, args=(), daemon=True).start()  # 处理插件消息
            threading.Thread(target=self.file, args=(), daemon=True).start()  # 处理筛选器消息
            threading.Thread(target=self.filter, args=(), daemon=True).start()  # 处理筛选器消息
            threading.Thread(target=self.system, args=(), daemon=True).start()  # 系统插件处理器
            threading.Thread(target=self.monitor, args=(), daemon=True).start()  # 处理无用消息
            threading.Thread(target=timer_manager.handle_command,
                             args=(glob_instance.ws, config["timer_gids_list"]), daemon=True).start()  # 启动定时器

    def unwrap_quote(self, m):
        return m.replace("&", "&").replace("[", "[").replace("]", "]").replace(",", ",")

    def handle_message(self, message):
        if "post_type" not in message or message['post_type'] != "message":
            return None, None, None, None

        for message_data in message["message"]:
            if message_data["type"] == "text":
                message_data["data"]["text"] = self.unwrap_quote(message_data["data"]["text"])

        # 提取数据
        uid = message["user_id"]
        nickname = message["sender"]["nickname"]
        message_dict = {
            "raw_message": self.unwrap_quote(message["raw_message"]),
            "message": message["message"],
            'message_id': message.get('message_id', None)
        }
        gid = message.get("group_id", None)

        return uid, nickname, gid, message_dict

    def process_queue(self, handler, *args):
        while not self.stop_event.is_set():
            if self.message_queue.empty():
                time.sleep(0.1)
                continue
            for item in list(self.message_queue.queue):
                if handler(item, *args):
                    try:
                        self.message_queue.queue.remove(item)
                        break
                    except:
                        logger.debug("该队列信息不存在或已被移除")
                        break

    def filter(self):
        def filter_handler(item):
            websocket, uid, gid, message_dict = item[0], item[1], item[3], item[4]
            for filter_name, filter_rule in filter_manager.filter_info.items():
                if ban_filter(uid, gid, filter_name):
                    for message in message_dict['message']:
                        if filter_rule[0] == message["type"]:
                            logger.debug(f"过滤器触发")
                            filter_manager.handle_message(websocket, uid, gid, message_dict, message, filter_name)
                            return True
            return False

        if self.pause_message_processing:
            self.process_queue(filter_handler)

    def plugin(self):
        def plugin_handler(item):
            websocket, uid, nickname, gid, message_dict = item
            tmp_message = "".join([data['data']['text'] for data in message_dict['message'] if data['type'] == 'text'])
            if not tmp_message:
                return False

            command, *args = tmp_message.split()
            plugin_name = find_plugin_by_command(command, plugin_manager.plugin_info)
            if ban_plugin(uid, gid, plugin_name) and plugin_name is not None:
                logger.debug(f"功能调用触发")
                plugin_manager.handle_command(websocket, uid, gid, nickname, message_dict, plugin_name)
                return True
            return False

        if self.pause_message_processing:
            self.process_queue(plugin_handler)

    def file(self):
        def file_handler(item):
            websocket, uid, nickname, gid, message_dict = item
            if uid in config['admin'] and "file" in message_dict["message"][0]["data"]:
                file_name = message_dict["message"][0]["data"]["file"]
                if file_name in file_manager.file_info:
                    logger.debug(f"本地文件更新触发")
                    file_manager.handle_command(websocket, uid, gid, nickname, message_dict, file_name)
                    return True
            return False

        if self.pause_message_processing:
            self.process_queue(file_handler)

    def system(self):
        def system_handler(item):
            websocket, uid, nickname, gid, message_dict = item
            if uid in config["admin"]:
                tmp_message = "".join(
                    [data['data']['text'] for data in message_dict['message'] if data['type'] == 'text'])
                if not tmp_message:
                    return False

                command, *args = tmp_message.split()
                system_name = find_plugin_by_command(command, system_manager.system_info)
                if system_name is not None:
                    logger.debug(f"系统功能调用触发")
                    system_manager.handle_command(websocket, uid, gid, nickname, message_dict, system_name)
                    return True
            return False

        self.process_queue(system_handler)

    # 处理无效消息
    def monitor(self):
        def monitor_handler(item):
            time.sleep(0.2)
            try:
                if self.message_queue.queue[0] != item:
                    return False  # 如果消息发生变化，则不处理
            except IndexError:
                return False

            # 如果1秒后消息没有变化，则删除它
            logger.debug(f"监测到无用信息,已经从信息队列中删除: {item}")
            return True

        self.process_queue(monitor_handler)

    # 结束多线程任务
    def stop(self):
        self.stop_event.set()


messageprocess = MessageProcess()
