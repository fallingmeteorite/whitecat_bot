from common.log import logger
from common.config import config
from common.module_load import load
from scheduling.thread_scheduling import add_task


# 定义文件管理器类
class FileManager:
    def __init__(self):
        # 初始化文件管理器的核心字典：files
        self.files = {}
        self.files_asynchronous = {}

    # 注册插件的方法
    def register_plugin(self, name, asynchronous, handler):
        # 将文件的名称与处理函数关联
        self.files[name] = handler
        self.files_asynchronous[name] = asynchronous
        logger.debug(f"FILE |文件检测:{name}导入成功 |FILE")

    # 处理命令的异步方法

    def handle_command(self, websocket, uid, gid, nickname, message_dict, file):
        # 获取下载文件的处理函数
        handler = self.files[file]
        add_task(file, handler, self.files_asynchronous[file], websocket, uid, nickname, gid,
                 message_dict["message"][0]["data"]["file_id"])


File_dir = config["file_dir"]
file_manager = load(File_dir, FileManager)
