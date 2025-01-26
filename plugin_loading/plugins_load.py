import asyncio
import gc
import os
from typing import Dict, Any, Optional

from common.logging import logger
from memory_management.memory_release import memory_release_decorator
from module_processing.module_management import recorder
from module_processing.timer import trigger_timer
from plugin_loading.load_base import SimpleModuleLoader
from task_scheduling import asyntask, linetask

# 全局插件卸载管理器
uninstall_manager = None
# 设置垃圾回收的阈值，以优化内存管理
gc.set_threshold(20, 0, 0)


class PluginUninstall:
    """
    插件卸载器类，用于卸载已加载的插件。
    """

    logger.debug("正在卸载已加载插件信息和命令")

    # 注册过滤器并执行相应的卸载操作
    def register_filter(self, filter_name: str,
                        asynchronous: Optional[bool] = None,
                        timeout_processing: Optional[bool] = None,
                        handler: Optional[callable] = None,
                        filter_rule: Optional[dict] = None) -> None:

        # 强制停止与过滤器相关的异步任务和线性任务
        asyntask.force_stop_task(filter_name)
        linetask.force_stop_task(filter_name)
        # 从卸载管理器中删除过滤器信息
        del uninstall_manager.filter_info[filter_name]

    # 注册插件并执行相应的卸载操作
    def register_plugin(self, name: str,
                        commands: Optional[list] = None,
                        asynchronous: Optional[bool] = None,
                        timeout_processing: Optional[bool] = None,
                        handler: Optional[callable] = None) -> None:

        # 强制停止与插件相关的异步任务和线性任务
        asyntask.force_stop_task(name)
        linetask.force_stop_task(name)
        # 从卸载管理器中删除插件信息
        del uninstall_manager.plugin_info[name]

    # 注册文件并执行相应的卸载操作
    def register_file(self, name: str,
                        asynchronous: Optional[bool] = None,
                        timeout_processing: Optional[bool] = None,
                        handler: Optional[callable] = None) -> None:

        # 强制停止与文件相关的异步任务和线性任务
        asyntask.force_stop_task(name)
        linetask.force_stop_task(name)
        # 从卸载管理器中删除文件信息
        del uninstall_manager.file_info[name]

    # 注册定时器并执行相应的卸载操作
    def register_timer(self, timer_name: str,
                       target_time: Optional[int] = None,
                       handler: Optional[callable] = None) -> None:

        # 强制停止与定时器相关的异步任务和线性任务
        asyntask.force_stop_task(timer_name)
        linetask.force_stop_task(timer_name)


def get_directories(path: str) -> list:
    """
    获取指定文件夹内的所有子文件夹。

    :param path: 文件夹路径。
    :return: 子文件夹名称列表。
    """
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


@memory_release_decorator
def load(load_dir: str, Install: callable) -> tuple:
    """
    初始化加载插件（非热加载）。

    :param load_dir: 插件目录路径。
    :param Install: 插件管理器类。
    :return: (插件管理器实例, 加载的插件模块字典)。
    """
    load_module: Dict[str, Any] = {}
    manager = Install()  # 创建插件管理器实例

    # 遍历插件目录中的文件夹
    for folder in get_directories(load_dir):
        # 开始记录模块的导入
        recorder.start_recording(folder)

        # 创建模块加载器从文件位置导入插件模块
        loader = SimpleModuleLoader(folder, f"{load_dir}/{folder}/{folder}.py")
        # 加载模块
        module = loader.load_module()

        # 停止记录，检测新增的模块
        recorder.stop_recording()

        load_module[folder] = module
        # 检查并注册插件
        if hasattr(module, 'register'):
            module.register(manager)

        # 显式删除不再使用的变量
        del loader
        del module

    return manager, load_module


@memory_release_decorator
def reload(path_to_watch: str, original_folder: str, reload_enable: bool,
           target_folder: Optional[str], observer: Any,
           load_module: Dict[str, Any], install: Any) -> None:
    """
    插件的加载和卸载（热加载）。

    :param path_to_watch: 监视的插件目录路径。
    :param original_folder: 原始插件文件夹名称。
    :param reload_enable: 是否重新加载插件。
    :param target_folder: 目标插件文件夹名称（用于重命名操作）。
    :param observer: 文件监视器对象。
    :param load_module: 已加载的插件模块字典。
    :param install: 插件管理器实例。
    """
    from plugin_loading.file_monitor import start_monitoring
    # 重启倒计时
    trigger_timer()

    # 关闭观察者
    observer.stop()
    logger.debug("观察者已关闭, 正在执行插件加载操作, 请勿修改插件文件夹")

    # 创建插件卸载器实例
    uninstall = PluginUninstall()
    global uninstall_manager
    uninstall_manager = install

    try:
        # 处理插件加载和卸载逻辑
        if original_folder in load_module:
            # 卸载插件
            module = load_module[original_folder]
            del load_module[original_folder]
            module.register(uninstall)

            # 获取模块中的所有变量
            module_vars = module.__dict__
            # 删除模块中的变量
            for var_name in list(module_vars.keys()):
                if not var_name.startswith('__'):  # 过滤掉内置变量
                    delattr(module, var_name)  # 删除模块中的变量

            del uninstall_manager
            recorder.remove_module_and_referencers(original_folder)
            # 卸载模块并清理内存（通过模块对象卸载）
            SimpleModuleLoader.unload_module(None, module)

            # 手动释放内存
            collected = gc.collect()
            logger.debug(f"手动触发垃圾回收，释放了 {collected} 个对象。")

        if target_folder is None:  # 非重命名操作
            if reload_enable:
                # 开始记录模块的导入
                recorder.start_recording(original_folder)

                # 创建模块加载器从文件位置导入插件模块
                loader = SimpleModuleLoader(original_folder, f"{path_to_watch}/{original_folder}/{original_folder}.py")
                # 加载模块
                module = loader.load_module()

                # 停止记录，检测新增的模块
                recorder.stop_recording()

                load_module[original_folder] = module
                # 检查并注册插件
                if hasattr(module, 'register'):
                    module.register(install)

                # 显式删除不再使用的变量
                del loader
                del module

        else:  # 重命名操作
            if reload_enable:
                # 开始记录模块的导入
                recorder.start_recording(target_folder)

                # 创建模块加载器从文件位置导入插件模块
                loader = SimpleModuleLoader(target_folder, f"{path_to_watch}/{target_folder}/{target_folder}.py")
                # 加载模块
                module = loader.load_module()

                # 停止记录，检测新增的模块
                recorder.stop_recording()

                load_module[target_folder] = module
                # 检查并注册插件
                if hasattr(module, 'register'):
                    module.register(install)

                # 显式删除不再使用的变量
                del loader
                del module

    except Exception as error:
        logger.error(f"插件加载出现问题, 请确认插件是否存在错误, 报错信息: {error}")
    finally:
        # 重新启动文件监视器
        logger.debug("插件加载完毕, 观察者已开启, 可以修改插件文件夹")
        asyncio.run(start_monitoring(path_to_watch, load_module, install))

        # 显式删除不再使用的变量
        del path_to_watch
        del original_folder
        del reload_enable
        del target_folder
        del observer
        del load_module
        del install
