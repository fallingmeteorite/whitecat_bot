import asyncio
import gc
import importlib.util
import os

from common.log import logger
from scheduling.thread_scheduling import asyntask, linetask

uninstall_manager = None


# 定义插件卸载器类
class PluginUninstall:
    # 卸载插件的方法
    def register_plugin(self, name, commands=None, asynchronous=None, timeout_processing=None, handler=None,
                        filter_rule=None):
        logger.debug("正在卸载已加载插件信息和命令")
        # 判断要卸载的是什么插件
        if hasattr(uninstall_manager, "plugin_info"):
            del uninstall_manager.plugin_info[name]
        # 判断要卸载的是什么插件
        if hasattr(uninstall_manager, "file_info"):
            del uninstall_manager.file_info[name]
        # 判断要卸载的是什么插件
        if hasattr(uninstall_manager, "filter_info"):
            del uninstall_manager.filter_info[name]
        # 先结束定时器任务
        if hasattr(uninstall_manager, "time_tasks"):
            asyntask.force_stop_task(name)
            linetask.force_stop_task(name)


# 获取指定文件夹内所有文件夹
def get_directories(path):
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


# 初始化加载插件的方法(不是热加载)
def load(load_dir, Install):
    load_module = {}
    # 创建插件管理器实例
    manager = Install()
    # 遍历插件目录中的文件
    for folder in get_directories(load_dir):
        try:
            # 从文件位置导入插件模块
            spec = importlib.util.spec_from_file_location(folder, f"{load_dir}/{folder}/{folder}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # 写入加载的插件信息
            load_module[folder] = module
            # 检查并注册插件
            if hasattr(module, 'register'):
                module.register(manager)
        except Exception as error:
            logger.error(f"插件加载失败,也许你的插件存在错误,加载错误信息: {error}")
    return manager, load_module


# 插件的加载和卸载(热加载)
def reload(path_to_watch, original_folder, reload_enable, target_folder, observer, load_module, install):
    from common.file_monitor import start_monitoring
    # 关闭观察者
    observer.stop()
    logger.debug("观察者已经关闭,正在执行插件加载操作,请勿修改插件文件夹")
    # 创建插件加载卸载实例
    uninstall = PluginUninstall()

    global uninstall_manager
    uninstall_manager = install

    try:
        # 不是插件文件夹改名操作
        if target_folder is None:
            if not load_module.get(original_folder, "") == "":
                # 从文件位置导入插件,然后读取下信息用于卸载插件
                module = load_module[original_folder]
                # 卸载插件,因为已经加载了,所以一定有register就不检测了
                module.register(uninstall)
                # 删除加载在load_module_dict的信息
                del load_module[original_folder]

            if reload_enable:
                # 从文件位置导入插件模块
                spec = importlib.util.spec_from_file_location(original_folder,
                                                              f"{path_to_watch}/{original_folder}/{original_folder}.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # 写入加载的插件信息
                load_module[original_folder] = module

                # 检查并注册插件
                if hasattr(module, 'register'):
                    module.register(install)

        # 是插件文件夹改名操作
        if target_folder is not None:
            # 先卸载插件内容
            # 创建插件卸载器实例

            # 从文件位置导入插件,然后读取下信息用于卸载插件
            module = load_module[original_folder]
            # 卸载插件,因为已经加载了,所以一定有register就不检测了
            module.register(uninstall)
            # 删除加载在load_module_dict的信息
            del load_module[original_folder]

            if reload_enable:
                # 从文件位置导入插件模块
                spec = importlib.util.spec_from_file_location(target_folder,
                                                              f"{path_to_watch}/{target_folder}/{target_folder}.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # 写入加载的插件信息
                load_module[target_folder] = module
                # 检查并注册插件
                if hasattr(module, 'register'):
                    module.register(install)
    except Exception as error:
        logger.error(f"插件加载出现问题,请确认插件是否存在错误,报错信息: {error}")
    finally:
        logger.debug(f"主动回收内存中信息：{gc.collect()}")
        # 启动插件文件夹监视
        logger.debug("插件加载完毕,观察者已经开启,可以修改插件文件夹")
        asyncio.run(start_monitoring(path_to_watch, load_module, install))
        return None
