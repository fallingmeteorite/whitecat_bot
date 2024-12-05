import os
import threading
import time

from common.log import logger
from watchdog.observers import Observer
from watchdog.utils import FileSystemEventHandler

# 创建一个锁对象
lock = threading.Lock()
observer = None


def rate_limit(interval):
    """
    装饰器函数，防止被装饰的函数在指定的时间间隔内被多次调用。

    :param interval: 时间间隔（秒）
    """

    def decorator(func):
        last_called = 0  # 记录上次调用的时间

        def wrapper(*args, **kwargs):
            nonlocal last_called
            with lock:
                current_time = time.time()
                if current_time - last_called < interval:
                    pass
                    return None
                last_called = current_time
            return func(*args, **kwargs)

        return wrapper

    return decorator


class FolderChangeHandler(FileSystemEventHandler):
    def __init__(self, path_to_watch, observer, reload_plugin):
        self.path_to_watch = path_to_watch
        self.observer = observer
        self.reload_plugin = reload_plugin
        # 删除无用变量
        del path_to_watch, reload_plugin, observer

    # 用于对输出路径进行切割并取出和触发插件加载功能,输入的全是修改前的路径
    @rate_limit(4)
    def get_observe_folder(self, original_dir, target_dir, type_operation):
        original_folder = original_dir.replace("\\", "/").split('/')[2]
        logger.debug(f"监测到插件文件夹被修改,开始重新加载修改插件,执行操作类型: {type_operation}")

        # 判断是不是给插件文件夹修改名字
        if type_operation == "moved" and not os.path.exists(f"{original_dir}/{original_folder}"):
            target_folder = target_dir.replace("\\", "/").split('/')[2]
            self.reload_plugin(self.path_to_watch, original_folder, True, target_folder, self.observer)

        # 判断是不是删除插件
        if type_operation == "deleted" and not os.path.exists(f"{original_dir}/{original_folder}"):
            self.reload_plugin(self.path_to_watch, original_folder, False, None, self.observer)

        # 删除插件文件夹内文件
        if type_operation == "deleted" and os.path.exists(f"{original_dir}/{original_folder}"):
            self.reload_plugin(self.path_to_watch, original_folder, True, None, self.observer)

        # 移动插件文件夹内文件
        if type_operation == "moved" and os.path.exists(f"{original_dir}/{original_folder}"):
            self.reload_plugin(self.path_to_watch, original_folder, True, None, self.observer)

        if type_operation == "modified":
            self.reload_plugin(self.path_to_watch, original_folder, True, None, self.observer)

        if type_operation == "created":
            self.reload_plugin(self.path_to_watch, original_folder, True, None, self.observer)

    @rate_limit(4)
    def on_deleted(self, event):
        self.get_observe_folder(event.src_path, None, type_operation="deleted")

    @rate_limit(4)
    def on_created(self, event):
        self.get_observe_folder(event.src_path, None, type_operation="created")

    @rate_limit(4)
    def on_modified(self, event):
        self.get_observe_folder(event.src_path, None, type_operation="modified")

    @rate_limit(4)
    def on_moved(self, event):
        self.get_observe_folder(event.src_path, event.dest_path, type_operation="moved")


async def start_monitoring(path_to_watch, reload_plugin):
    # 创建观察者对象
    observer = Observer()

    # 创建事件处理器
    event_handler = FolderChangeHandler(path_to_watch, observer, reload_plugin)
    observer.schedule(event_handler, path=path_to_watch, recursive=True)
    # 启动观察者
    observer.start()
    logger.debug(f"文件监测已经开启,监测目录{path_to_watch}")
