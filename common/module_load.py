import importlib.util
import os

from common.config import config
from common.log import logger


# 获取指定文件夹内所有文件夹
def get_directories(path):
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


# 初始化加载插件的方法(不是热加载)
def load(load_dir, Install):
    load_module_dict = {}

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

            load_module_dict[folder] = module

            # 检查并注册插件
            if hasattr(module, 'register'):
                module.register(manager)

        except Exception as error:
            logger.error(f"加载失败,也许你的插件存在错误,加载错误信息: {error}")
    # 当是插件文件夹时候，要将修改应用到全局变量
    if load_dir == config["plugin_dir"]:
        return manager, load_module_dict
    else:
        # 返回管理器实例
        return manager
