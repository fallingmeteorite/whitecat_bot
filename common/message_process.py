import queue
import threading
import time

from common.config import config
from common.log import logger
from manager.block_manager import ban_filter, ban_plugin
from manager.file_manager import file_manager
from manager.filter_manager import filter_manager
from manager.plugin_manager import plugin_manager, find_plugin_by_command


class MessageProcess:

    def __init__(self):
        self.message_queue = queue.Queue()
        # 用于判断消息处理线程是否开启
        self.lock = False
        # 当主程序的关闭时,用于关闭消息处理线程
        self.stop_event = threading.Event()  # 用于控制线程停止的事件

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
            threading.Thread(target=self.plugin, args=()).start()  # 处理插件消息
            threading.Thread(target=self.file, args=()).start()  # 处理筛选器消息
            threading.Thread(target=self.filter, args=()).start()  # 处理筛选器消息
            threading.Thread(target=self.monitor, args=()).start()  # 处理无用消息

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
            # 将过滤器的判断逻辑移到这里
            for item in list(self.message_queue.queue):
                # 获取队列中的信息但是不修改队列
                websocket, uid, nickname, gid, message_dict = item
                for filter_name, filter_rule in filter_manager.filters.items():
                    if ban_filter(uid, gid, filter_name):
                        for message in message_dict['message']:
                            # 如果找到匹配项，则处理消息
                            if filter_rule == message["type"]:
                                logger.debug(f"过滤器触发")
                                # 从队列中移除匹配项,防止占用队列空间
                                self.message_queue.queue.remove(item)
                                filter_manager.handle_message(websocket, uid, gid, message_dict, message,
                                                              filter_name)
                                break



    def plugin(self):
        while not self.stop_event.is_set():
            if self.message_queue.empty():
                time.sleep(0.1)  # 队列为空时短暂休眠
                continue
            # 将插件加载器的判断逻辑移到这里
            for item in list(self.message_queue.queue):
                websocket, uid, nickname, gid, message_dict = item
                # 解析命令和参数
                tmp_message = ""
                message_list = message_dict['message']
                for data in message_list:
                    if data['type'] == 'text':
                        tmp_message = tmp_message + data['data']['text']
                if tmp_message == "":
                    # 如果没有消息,跳出这次循环
                    continue

                command, *args = tmp_message.split()

                # 通过命令查找对应的插件
                plugin_name = find_plugin_by_command(command, plugin_manager.plugin_info)
                if ban_plugin(uid, gid, plugin_name):
                    if plugin_name is not None:
                        # :param uid: 用户ID。
                        # :param gid: 群组ID。
                        # 对限制使用次数的群做处理,查看是否达到最大使用次数,是则不执行

                        logger.debug(f"功能调用触发")
                        # 从队列中移除匹配项,防止占用队列空间
                        self.message_queue.queue.remove(item)
                        plugin_manager.handle_command(websocket, uid, gid, nickname, message_dict, plugin_name)
                        break


    def file(self):
        while not self.stop_event.is_set():
            if self.message_queue.empty():
                time.sleep(0.1)  # 队列为空时短暂休眠
                continue

            for item in list(self.message_queue.queue):
                websocket, uid, nickname, gid, message_dict = item
                if uid in config['admin'] and (message_dict["message"][0]["data"]).get(("file"), None) is not None:
                    # 查看文件加载字典中是否有这个文件对应的处理
                    if file_manager.files.get(message_dict["message"][0]["data"]["file"], None) is not None:
                        logger.debug(f"本地文件更新触发")
                        # 从队列中移除匹配项,防止占用队列空间
                        self.message_queue.queue.remove(item)
                        file_manager.handle_command(websocket, uid, gid, nickname, message_dict,
                                                    message_dict["message"][0]["data"]["file"])
                        break


    # 处理无效消息
    def monitor(self):
        count = 0
        while not self.stop_event.is_set():
            time.sleep(0.5)  # 每0.5检查一次
            if self.message_queue.empty():
                continue
            now_message = self.message_queue.queue[0]
            # 如果消息队列第一个信息未变化
            if self.message_queue.queue[0] == now_message:
                count += 1
                if count >= 2:
                    none = self.message_queue.get()
                    logger.debug(f"监测到无用信息,已经从信息队列中删除: {none}")
                    count = 0

    # 结束多线程任务
    def stop(self):
        self.stop_event.set()


# 实例化对象
messageprocess = MessageProcess()

# 主程序结束时调用 stop 方法
# messageprocess.stop()
