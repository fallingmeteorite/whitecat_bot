import os
import threading
import time

from common.log import logger
from common.module_load import reload
from watchdog.observers import Observer
from watchdog.utils.events import FileSystemEventHandler

# 创建一个锁对象
lock = threading.Lock()


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
                    return None
                last_called = current_time
            return func(*args, **kwargs)

        return wrapper

    return decorator


class FolderChangeHandler(FileSystemEventHandler):
    def __init__(self, path_to_watch, observer, load_module, manager):
        self.path_to_watch = path_to_watch
        self.observer = observer
        self.load_module = load_module
        self.manager = manager

    def get_folder_name(self, path):
        return path.replace("\\", "/").split('/')[2]

    @rate_limit(4)
    def handle_folder_change(self, original_dir, target_dir=None, type_operation=None):
        original_folder = self.get_folder_name(original_dir)
        logger.debug(f"监测到插件文件夹被修改,开始重新加载修改插件,执行操作类型: {type_operation}")

        if type_operation == "moved":
            if not os.path.exists(original_dir):
                target_folder = self.get_folder_name(target_dir)
                reload(self.path_to_watch, original_folder, True, target_folder, self.observer, self.load_module, self.manager)
            else:
                reload(self.path_to_watch, original_folder, True, None, self.observer, self.load_module, self.manager)

        elif type_operation == "deleted":
            if not os.path.exists(original_dir):
                reload(self.path_to_watch, original_folder, False, None, self.observer, self.load_module, self.manager)
            else:
                reload(self.path_to_watch, original_folder, True, None, self.observer, self.load_module, self.manager)

        elif type_operation in ["modified", "created"]:
            reload(self.path_to_watch, original_folder, True, None, self.observer, self.load_module, self.manager)

    @rate_limit(4)
    def on_deleted(self, event):
        self.handle_folder_change(event.src_path, type_operation="deleted")

    @rate_limit(4)
    def on_created(self, event):
        self.handle_folder_change(event.src_path, type_operation="created")

    @rate_limit(4)
    def on_modified(self, event):
        self.handle_folder_change(event.src_path, type_operation="modified")

    @rate_limit(4)
    def on_moved(self, event):
        self.handle_folder_change(event.src_path, event.dest_path, type_operation="moved")


async def start_monitoring(path_to_watch, load_module, manager):
    observer = Observer()
    event_handler = FolderChangeHandler(path_to_watch, observer, load_module, manager)
    observer.schedule(event_handler, path=path_to_watch, recursive=True)

    observer.start()
    logger.debug(f"文件监测已经开启,监测目录{path_to_watch}")
