import asyncio
import gc
import importlib.util

from common.config import config
from common.file_monitor import start_monitoring
from common.log import logger
from common.module_load import load
from scheduling.thread_scheduling import add_task

load_module_dict = {}


# 获取命令调用的插件
def find_plugin_by_command(command, plugin_commands):
    for plugin_name, plugin_info in plugin_commands.items():
        if command in plugin_info.get('commands', []):
            return plugin_name
    return None


# 定义插件管理器类
class PluginManager:
    def __init__(self):
        # 初始化插件管理器的两个核心字典：plugins和plugin_info
        self.plugins = {}
        self.plugin_info = {}
        self.plugins_asynchronous = {}

    # 注册插件的方法
    def register_plugin(self, name, asynchronous, commands, handler):
        # 将插件的名称与处理函数关联
        self.plugins[name] = handler
        self.plugins_asynchronous[name] = asynchronous
        # 将插件的详细信息，如命令、帮助文本和帮助处理函数关联
        self.plugin_info[name] = {
            "commands": commands,
        }
        logger.debug(f"FUNC| 插件:{name}导入成功 |FUNC")

    # 处理命令的异步方法
    def handle_command(self, websocket, uid, gid, nickname, message_dict, plugin_name):
        handler = self.plugins[plugin_name]
        add_task(plugin_name, handler, self.plugins_asynchronous[plugin_name], websocket, uid, nickname, gid,
                 message_dict)


# 定义插件卸载器类
class PluginUninstall:

    # 卸载插件的方法
    def register_plugin(self, name, asynchronous, commands, handler):
        # 将插件的名称与处理函数关联
        del plugin_manager.plugins[name]
        del plugin_manager.plugin_info[name]
        del plugin_manager.plugins_asynchronous[name]


# 插件的加载和卸载(热加载)
def reload_plugin(path_to_watch: str, original_folder: str, reload_enable: bool, target_folder: str,
                  observer):
    # 关闭观察者
    observer.stop()
    logger.debug("观察者已经关闭,正在执行插件加载操作,请勿修改插件文件夹")

    # 声明全局变量,方便操作
    global load_module_dict
    try:

        # 不是插件文件夹改名操作
        if target_folder is None:
            if not load_module_dict.get(original_folder, "") == "":
                # 先卸载插件内容
                # 创建插件卸载器实例
                plugin_uninstall = PluginUninstall()
                # 从文件位置导入插件,然后读取下信息用于卸载插件
                module = load_module_dict[original_folder]
                # 卸载插件,因为已经加载了,所以一定有register就不检测了
                module.register(plugin_uninstall)
                # 删除加载在load_module_dict的信息
                del load_module_dict[original_folder]

            if reload_enable:
                logger.debug("开始加载插件")
                # 重新加载插件
                # 从文件位置导入插件模块
                spec = importlib.util.spec_from_file_location(original_folder,
                                                              f"{path_to_watch}/{original_folder}/{original_folder}.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # 写入加载的插件信息
                load_module_dict[original_folder] = module

                # 检查并注册插件
                if hasattr(module, 'register'):
                    module.register(plugin_manager)
                logger.debug("插件加载完成")

        # 是插件文件夹改名操作
        if target_folder is not None:
            # 先卸载插件内容
            # 创建插件卸载器实例
            plugin_uninstall = PluginUninstall()
            # 从文件位置导入插件,然后读取下信息用于卸载插件
            module = load_module_dict[original_folder]
            # 卸载插件,因为已经加载了,所以一定有register就不检测了
            module.register(plugin_uninstall)
            # 删除加载在load_module_dict的信息
            del load_module_dict[original_folder]

            if reload_enable:
                logger.debug("开始加载插件")
                # 重新加载插件
                # 从文件位置导入插件模块
                spec = importlib.util.spec_from_file_location(target_folder,
                                                              f"{path_to_watch}/{target_folder}/{target_folder}.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # 写入加载的插件信息
                load_module_dict[target_folder] = module

                # 检查并注册插件
                if hasattr(module, 'register'):
                    module.register(plugin_manager)
                logger.debug("插件加载完成")
    except Exception as error:
        logger.error(f"插件加载出现问题,请确认插件是否存在错误,报错信息: {error}")
        logger.debug(f"主动回收内存中信息：{gc.collect()}")
    finally:
        logger.debug(f"主动回收内存中信息：{gc.collect()}")

        # 启动插件文件夹监视
        logger.debug("插件加载完毕,观察者已经开启,可以修改插件文件夹")
        asyncio.run(start_monitoring(plugin_dir, reload_plugin))


plugin_dir = config["plugin_dir"]
plugin_manager, load_module_dict = load(plugin_dir, PluginManager)

# 判断开不开启插件热加载
enable_hot_loading = config["enable_hot_loading"]
if enable_hot_loading:
    # 启动插件文件夹监视
    asyncio.run(start_monitoring(plugin_dir, reload_plugin))
