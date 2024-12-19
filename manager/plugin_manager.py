import asyncio

from common.config import config
from common.log import logger
from common.message_send import send_message
from common.module_load import load
from manager.user_manager import tracker
from scheduling.thread_scheduling import add_task


# 获取命令调用的插件
def find_plugin_by_command(command, plugin_commands):
    for info in plugin_commands.items():
        if command in info[1][2]:
            return info[0]
    return None


# 定义插件管理器类
class PluginManager:
    def __init__(self):
        # 初始化插件管理器的两个核心字典：plugins和plugin_info
        self.plugin_info = {}

    # 注册插件的方法
    def register_plugin(self, name, asynchronous, timeout_processing, commands, handler):
        # 将插件的名称与处理函数关联
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.plugin_info[name] = (asynchronous, timeout_processing, commands, handler)
        logger.debug(f"FUNC| 插件:{name}导入成功 |FUNC")

    # 处理命令的方法
    def handle_command(self, websocket, uid, gid, nickname, message_dict, plugin_name):
        if tracker.use_detections(uid, gid):
            asynchronous, timeout_processing, _, handler = self.plugin_info[plugin_name]
            add_task(timeout_processing, plugin_name, handler, asynchronous, websocket, uid, nickname, gid,
                     message_dict)
        else:
            send_message(websocket, None, gid, message="今天你的使用次数到达上线了,休息一会吧")


plugin_dir = config["plugin_dir"]
plugin_manager, load_module = load(plugin_dir, PluginManager)

# 判断开不开启插件热加载
enable_hot_loading = config["enable_hot_loading"]
if enable_hot_loading:
    from common.file_monitor import start_monitoring

    # 启动插件文件夹监视
    asyncio.run(start_monitoring(plugin_dir, load_module, plugin_manager))
