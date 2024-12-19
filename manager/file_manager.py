import asyncio

from common.config import config
from common.log import logger
from common.module_load import load
from scheduling.thread_scheduling import add_task


# 定义文件管理器类
class FileManager:
    def __init__(self):
        # 初始化文件管理器的核心字典：file_info
        self.file_info = {}

    # 注册插件的方法
    def register_plugin(self, name, asynchronous, timeout_processing, handler):
        # 将文件的名称与处理函数关联
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.file_info[name] = (asynchronous, timeout_processing, handler)
        logger.debug(f"FILE |文件检测:{name}导入成功 |FILE")

    # 处理命令的方法
    def handle_command(self, websocket, uid, gid, nickname, message_dict, file):
        # 获取下载文件的处理函数
        asynchronous, timeout_processing, handler = self.file_info[file]
        add_task(timeout_processing, file, handler, asynchronous, websocket, uid, nickname, gid,
                 message_dict["message"][0]["data"]["file_id"])


file_dir = config["file_dir"]
file_manager, load_module = load(file_dir, FileManager)

# 判断开不开启插件热加载
enable_hot_loading = config["enable_hot_loading"]
if enable_hot_loading:
    from common.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(file_dir, load_module, file_manager))
