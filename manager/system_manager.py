from common.config import config
from common.logging import logger
from common.module_load import load
from scheduling.thread_scheduling import add_task


# 定义系统插件管理器类
class SystemManager:
    def __init__(self):
        # 初始化插件管理器的核心字典system_info
        self.system_info = {}

    # 注册插件的方法
    def register_system(self, name, asynchronous, timeout_processing, commands, handler):
        # 将插件的名称与处理函数关联
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.system_info[name] = (asynchronous, timeout_processing, commands, handler)
        logger.debug(f"SYSTEM| 系统插件:{name}导入成功 |SYSTEM")

    # 处理命令的方法
    def handle_command(self, websocket, uid, gid, nickname, message_dict, system_name):
        asynchronous, timeout_processing, _, handler = self.system_info[system_name]
        add_task(timeout_processing, system_name, handler, asynchronous, websocket, uid, nickname, gid, message_dict)


system_dir = config["system_dir"]
system_manager, _ = load(system_dir, SystemManager)
