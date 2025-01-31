import threading
import time
import weakref
from functools import lru_cache

from common import logger
from plugin_loading.plugins_load import reload
from watchdog import Observer, FileSystemEventHandler

# 创建一个全局锁对象，用于线程同步
lock = threading.Lock()


def rate_limit(interval: int):
    """
    装饰器函数，用于限制被装饰的函数在指定时间间隔内只能被调用一次。

    :param interval: 时间间隔（秒），在此间隔内函数不会被重复调用
    """

    def decorator(func):
        last_called = 0  # 记录函数上次被调用的时间

        def wrapper(*args, **kwargs):
            nonlocal last_called
            current_time = time.time()
            # 如果当前时间与上次调用时间的差值小于间隔时间，则直接返回，不执行函数
            if current_time - last_called < interval:
                return None
            last_called = current_time  # 更新上次调用时间
            result = func(*args, **kwargs)  # 执行被装饰的函数
            return result

        return wrapper

    return decorator


class FolderChangeHandler(FileSystemEventHandler):
    """
    文件夹变化事件处理器，继承自 `FileSystemEventHandler`。
    用于监听文件夹的变化（如创建、删除、修改、移动等），并触发相应的处理逻辑。
    """

    def __init__(self, path_to_watch: str, observer: Observer, load_module: callable, manager: object) -> None:
        """
        初始化文件夹变化事件处理器。

        :param path_to_watch: 要监听的文件夹路径
        :param observer: Watchdog 的 Observer 对象，用于管理监听器
        :param load_module: 加载模块的函数
        :param manager: 管理模块的对象
        """
        self.path_to_watch = path_to_watch
        self.observer = weakref.ref(observer)()  # 使用弱引用保存 Observer 对象
        self.load_module = load_module
        self.manager = manager

    @lru_cache(maxsize=128)
    def get_folder_name(self, path: str) -> str:
        """
        从路径中提取文件夹名称，并使用缓存优化性能。

        :param path: 文件或文件夹的完整路径
        :return: 文件夹名称
        """
        folder_name = path.replace("\\", "/").split('/')[2]  # 将路径中的反斜杠替换为斜杠，并取第三部分
        return folder_name

    @rate_limit(2)
    def handle_folder_change(self, original_dir: str, target_dir: str = None, type_operation: str = None) -> None:
        """
        处理文件夹变化的通用逻辑，根据操作类型调用 `reload` 函数。

        :param original_dir: 原始文件夹路径
        :param target_dir: 目标文件夹路径（仅用于移动操作）
        :param type_operation: 操作类型（如 "created", "deleted", "modified", "moved"）
        """
        original_folder = self.get_folder_name(original_dir)
        logger.debug(f"监测到插件文件夹被修改,开始重新加载修改插件,执行操作类型: {type_operation}")

        if self.observer is None:  # 如果 Observer 已被销毁，则返回
            logger.warning("Observer 已被销毁，无法处理文件夹变化。")
            return

        if type_operation == "moved":
            target_folder = self.get_folder_name(target_dir) if target_dir else None
            reload(self.path_to_watch, original_folder, True, target_folder, self.observer, self.load_module,
                   self.manager)
            del target_folder

        elif type_operation == "deleted":
            reload(self.path_to_watch, original_folder, False, None, self.observer, self.load_module, self.manager)

        elif type_operation in ["modified", "created"]:
            reload(self.path_to_watch, original_folder, True, None, self.observer, self.load_module, self.manager)

        # 显式删除不再使用的变量
        del original_folder
        del type_operation

    @rate_limit(2)
    def on_deleted(self, event) -> None:
        """
        处理文件夹或文件删除事件。

        :param event: Watchdog 的事件对象，包含事件的相关信息
        """
        self.handle_folder_change(event.src_path, type_operation="deleted")

    @rate_limit(2)
    def on_created(self, event) -> None:
        """
        处理文件夹或文件创建事件。

        :param event: Watchdog 的事件对象，包含事件的相关信息
        """
        self.handle_folder_change(event.src_path, type_operation="created")

    @rate_limit(2)
    def on_modified(self, event) -> None:
        """
        处理文件夹或文件修改事件。

        :param event: Watchdog 的事件对象，包含事件的相关信息
        """
        self.handle_folder_change(event.src_path, type_operation="modified")

    @rate_limit(2)
    def on_moved(self, event) -> None:
        """
        处理文件夹或文件移动事件。

        :param event: Watchdog 的事件对象，包含事件的相关信息
        """
        self.handle_folder_change(event.src_path, event.dest_path, type_operation="moved")


async def start_monitoring(path_to_watch: str, load_module: callable, manager: object) -> None:
    """
    启动文件夹监听功能。

    :param path_to_watch: 要监听的文件夹路径
    :param load_module: 加载模块的函数
    :param manager: 管理模块的对象
    """
    observer = Observer()  # 创建 Watchdog 的 Observer 对象
    event_handler = FolderChangeHandler(path_to_watch, observer, load_module, manager)  # 创建事件处理器
    observer.schedule(event_handler, path=path_to_watch, recursive=True)  # 将事件处理器绑定到指定路径

    observer.start()  # 启动监听器
    logger.debug(f"文件夹监测已经开启,监测文件夹目录: {path_to_watch}")

    # 显式删除不再使用的变量
    del observer
    del event_handler
