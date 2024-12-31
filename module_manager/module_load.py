import ast
import asyncio
import gc
import importlib.util
import os
from typing import Dict, Any, Optional, Set, List

from common.logging import logger
from core.memory_release import memory_release_decorator, unload_modules_from_folder, clear_variables_from_folder
from module_manager.module_unload import force_unload_unused_modules
from scheduling.thread_scheduling import asyntask, linetask

# 全局插件卸载管理器
uninstall_manager = None


class PluginUninstall:
    """
    插件卸载器类，用于卸载已加载的插件。
    """

    def register_plugin(self, name: str, commands: Optional[list] = None, asynchronous: Optional[bool] = None,
                        timeout_processing: Optional[bool] = None, handler: Optional[callable] = None,
                        filter_rule: Optional[dict] = None) -> None:
        """
        卸载已加载的插件信息和命令。

        Args:
            name: 插件名称。
            commands: 插件命令列表（可选）。
            asynchronous: 是否异步执行（可选）。
            timeout_processing: 是否启用超时处理（可选）。
            handler: 插件处理函数（可选）。
            filter_rule: 过滤器规则（可选）。
        """
        logger.debug("正在卸载已加载插件信息和命令")

        # 判断要卸载的是什么插件，并执行相应的卸载操作
        if hasattr(uninstall_manager, "plugin_info") and name in uninstall_manager.plugin_info:
            asyntask.force_stop_task(name)
            linetask.force_stop_task(name)
            del uninstall_manager.plugin_info[name]

        if hasattr(uninstall_manager, "file_info") and name in uninstall_manager.file_info:
            asyntask.force_stop_task(name)
            linetask.force_stop_task(name)
            del uninstall_manager.file_info[name]

        if hasattr(uninstall_manager, "filter_info") and name in uninstall_manager.filter_info:
            asyntask.force_stop_task(name)
            linetask.force_stop_task(name)
            del uninstall_manager.filter_info[name]

        # 结束定时器任务
        if hasattr(uninstall_manager, "time_tasks"):
            asyntask.force_stop_task(name)
            linetask.force_stop_task(name)


def extract_imports(file_path: str) -> List[str]:
    """
    从 Python 文件中提取所有导入的模块。

    Args:
        file_path (str): Python 文件的路径。

    Returns:
        List[str]: 排序后的导入模块列表。
    """
    with open(file_path, "r", encoding="utf-8") as file:
        tree = ast.parse(file.read(), filename=file_path)

    imports: Set[str] = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            imports.add(module)

    return sorted(imports)


def get_directories(path: str) -> list:
    """
    获取指定文件夹内的所有子文件夹。

    Args:
        path: 文件夹路径。

    Returns:
        list: 子文件夹名称列表。
    """
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


def load(load_dir: str, Install: callable) -> tuple:
    """
    初始化加载插件（非热加载）。

    Args:
        load_dir: 插件目录路径。
        Install: 插件管理器类。

    Returns:
        tuple: (插件管理器实例, 加载的插件模块字典)。
    """
    load_module: Dict[str, Any] = {}
    manager = Install()  # 创建插件管理器实例

    # 遍历插件目录中的文件夹
    for folder in get_directories(load_dir):
        try:
            # 从文件位置导入插件模块
            spec = importlib.util.spec_from_file_location(folder, f"{load_dir}/{folder}/{folder}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 写入加载的插件信息
            imports = extract_imports(f"{load_dir}/{folder}/{folder}.py")
            load_module[folder] = [module, imports]

            # 检查并注册插件
            if hasattr(module, 'register'):
                module.register(manager)
            del module, spec, imports
        except Exception as error:
            logger.error(f"插件加载失败, 可能插件存在错误, 错误信息: {error}")
        finally:
            logger.debug(f"主动回收内存为:{gc.collect()}")
    return manager, load_module


@memory_release_decorator
def reload(path_to_watch: str, original_folder: str, reload_enable: bool, target_folder: Optional[str],
           observer: Any, load_module: Dict[str, Any], install: Any) -> None:
    """
    插件的加载和卸载（热加载）。

    Args:
        path_to_watch: 监视的插件目录路径。
        original_folder: 原始插件文件夹名称。
        reload_enable: 是否重新加载插件。
        target_folder: 目标插件文件夹名称（用于重命名操作）。
        observer: 文件监视器对象。
        load_module: 已加载的插件模块字典。
        install: 插件管理器实例。
    """
    from common.file_monitor import start_monitoring

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
            module = load_module[original_folder][0]
            module.register(uninstall)

            # 删除库的引用和变量
            force_unload_unused_modules(load_module[original_folder][1])
            folder_to_clear = f"{path_to_watch}/{original_folder}"
            unload_modules_from_folder(folder_to_clear)
            clear_variables_from_folder(folder_to_clear)

            del load_module[original_folder]
            uninstall_manager = None

        if target_folder is None:  # 非重命名操作
            if reload_enable:
                # 重新加载插件
                spec = importlib.util.spec_from_file_location(original_folder,
                                                              f"{path_to_watch}/{original_folder}/{original_folder}.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # 写入加载的插件信息
                imports = extract_imports(f"{path_to_watch}/{original_folder}/{original_folder}.py")
                load_module[original_folder] = [module, imports]

                if hasattr(module, 'register'):
                    module.register(install)
                del module, spec, imports


        else:  # 重命名操作
            if reload_enable:
                # 加载重命名后的插件
                spec = importlib.util.spec_from_file_location(target_folder,
                                                              f"{path_to_watch}/{target_folder}/{target_folder}.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                imports = extract_imports(f"{path_to_watch}/{target_folder}/{target_folder}.py")
                load_module[target_folder] = [module, imports]

                if hasattr(module, 'register'):
                    module.register(install)
                del module, spec, imports

    except Exception as error:
        logger.error(f"插件加载出现问题, 请确认插件是否存在错误, 报错信息: {error}")
    finally:
        logger.debug(f"主动回收内存为:{gc.collect()}")
        # 重新启动文件监视器
        logger.debug("插件加载完毕, 观察者已开启, 可以修改插件文件夹")
        asyncio.run(start_monitoring(path_to_watch, load_module, install))