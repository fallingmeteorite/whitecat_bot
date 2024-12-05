import queue
import threading
import time
from common.log import logger
from common.config import config
from manager.plugin_manager import plugin_manager, find_plugin_by_command
from manager.file_manager import file_manager
from manager.filter_manager import filter_manager
from manager.user_manager import tracker


class MessageProcess:

    def __init__(self):
        self.message_queue = queue.Queue()
        self.lock = False
        self.stop_event = threading.Event()  # 用于控制线程停止的事件

    def add_message(self, websocket, message):
        uid, nickname, gid, message_dict = self.handle_message(message)
        if uid is not None or nickname is not None or message_dict is not None:
            logger.info(f"收到服务器有效数据: {uid, nickname, gid, message_dict}\n")
            self.message_queue.put((websocket, uid, nickname, gid, message_dict))

        if not self.lock:
            self.lock = True
            threading.Thread(target=self.plugin, args=()).start()
            threading.Thread(target=self.file, args=()).start()
            threading.Thread(target=self.filter, args=()).start()
            threading.Thread(target=self.monitor, args=()).start()

    def unwrap_quote(self, m):
        return m.replace("&", "&").replace("[", "[").replace("]", "]").replace(",", ",")

    def handle_message(self, message):
        # 检查 post_type
        if "post_type" not in message:
            return None, None, None, None
        if message['post_type'] != "message":
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
        # 处理 group_id
        gid = message.get("group_id", None)

        return uid, nickname, gid, message_dict

    def filter(self):
        while not self.stop_event.is_set():
            if self.message_queue.empty():
                time.sleep(0.1)  # 队列为空时短暂休眠
                continue

            for item in list(self.message_queue.queue):
                websocket, uid, nickname, gid, message_dict = item
                message_list = message_dict['message']
                if gid in config['valid_listen_gids'] or uid in config['valid_listen_uids']:
                    for filter_name, filter_rule in filter_manager.filters.items():
                        for message in message_list:
                            # 如果找到匹配项，则处理消息
                            if filter_rule == message["type"]:
                                logger.debug(f"过滤器触发")
                                self.message_queue.queue.remove(item)  # 从队列中移除匹配项
                                filter_manager.handle_message(websocket, uid, gid, message_dict, message, filter_name)
                                break

    def plugin(self):
        while not self.stop_event.is_set():
            if self.message_queue.empty():
                time.sleep(0.1)  # 队列为空时短暂休眠
                continue

            for item in list(self.message_queue.queue):
                websocket, uid, nickname, gid, message_dict = item
                if uid in config['admin'] or (
                        gid not in config['ban_plugin_gids'] and uid not in config['ban_plugin_uids']):
                    # 解析命令和参数
                    tmp_message = ""
                    message_list = message_dict['message']
                    for data in message_list:
                        if data['type'] == 'text':
                            tmp_message = tmp_message + data['data']['text']
                    if tmp_message == "":
                        continue

                    command, *args = tmp_message.split()

                    # 通过命令查找对应的插件
                    plugin_name = find_plugin_by_command(command, plugin_manager.plugin_info)
                    if plugin_name is not None:
                        # :param uid: 用户ID。
                        # :param gid: 群组ID。
                        if tracker.use_detections(uid, gid):
                            logger.debug(f"功能调用触发")
                            self.message_queue.queue.remove(item)  # 从队列中移除匹配项
                            plugin_manager.handle_command(websocket, uid, gid, nickname, message_dict, plugin_name)

    def file(self):
        while not self.stop_event.is_set():
            if self.message_queue.empty():
                time.sleep(0.1)  # 队列为空时短暂休眠
                continue

            for item in list(self.message_queue.queue):
                websocket, uid, nickname, gid, message_dict = item
                if uid in config['admin'] and (message_dict["message"][0]["data"]).get(("file"), None) is not None:
                    if file_manager.files.get(message_dict["message"][0]["data"]["file"], None) is not None:
                        logger.debug(f"本地文件更新触发")
                        self.message_queue.queue.remove(item)  # 从队列中移除匹配项
                        file_manager.handle_command(websocket, uid, gid, nickname, message_dict,
                                                    message_dict["message"][0]["data"]["file"])

    def monitor(self):
        count = 0
        while not self.stop_event.is_set():
            time.sleep(1)  # 每秒检查一次
            if self.message_queue.empty():
                continue
            now_message = self.message_queue.queue[0]
            if self.message_queue.queue[0] == now_message:
                count += 1
                if count >= 2:
                    none = self.message_queue.get()
                    logger.debug(f"监测到无用信息,信息删除,信息内容: {none}")
                    count = 0

    def stop(self):
        self.stop_event.set()


messageprocess = MessageProcess()

# 主程序结束时调用 stop 方法
# messageprocess.stop()
