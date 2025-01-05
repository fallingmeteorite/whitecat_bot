import ctypes
import functools
import gc
import inspect
import os
import sys
import weakref
from typing import Callable, Any, Dict

from common.config import config

# 根据操作系统加载对应的 C 库
if os.name == 'nt':  # Windows
    memory_cleaner = ctypes.CDLL('./memory_cleanup/memory_cleaner_win.dll')
else:  # Linux
    memory_cleaner = ctypes.CDLL('./memory_cleanup/memory_cleaner_linux.so')
memory_cleaner.clean_memory.restype = ctypes.c_size_t


def is_weakrefable(obj: Any) -> bool:
    """
    检查对象是否可以被弱引用。
    """
    try:
        weakref.ref(obj)
        return True
    except TypeError:
        return False


def get_object_source_path(obj: Any) -> str:
    """
    获取对象的源文件路径。
    """
    try:
        return inspect.getfile(obj)
    except (TypeError, OSError):
        return None


# 定义需要检查的路径列表
SPECIFIED_PATHS = [config['filters_dir'], config['file_dir'], config['plugin_dir'], config['timer_dir']]

def simple_memory_release_decorator(func: Callable) -> Callable:
    """
    简化版内存释放装饰器，仅用于正常回收内存。
    不处理指定路径，仅调用垃圾回收和 C 库的内存清理函数。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # 执行函数
        result = func(*args, **kwargs)
        # 调用 Python 的垃圾回收机制
        gc.collect()
        return result
    return wrapper

def memory_release_decorator(func: Callable) -> Callable:
    """
    内存释放装饰器，用于检查并清理不再被引用的模块、变量、类等对象。
    支持处理循环引用，并调用 C 代码进行复杂的内存清理。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # 获取函数执行前的所有模块
        before_modules = set(sys.modules.keys())

        # 使用弱引用字典存储新增变量
        weak_vars: Dict[str, weakref.ref] = {}

        # 执行函数
        result = func(*args, **kwargs)

        # 获取函数执行后的所有模块
        after_modules = set(sys.modules.keys())

        # 检查新增的模块
        new_modules = after_modules - before_modules

        # 检查模块是否来自指定路径
        for module_name in new_modules:
            module = sys.modules[module_name]
            source_path = get_object_source_path(module)
            if source_path and any(source_path.startswith(path) for path in SPECIFIED_PATHS):
                # 如果模块来自指定路径
                del sys.modules[module_name]  # 从 sys.modules 中移除
                print(f"Python: 已卸载未使用的模块: {module_name} (路径: {source_path})")

        # 获取所有对象并检查它们的源路径
        all_objects = gc.get_objects()
        for obj in all_objects:
            source_path = get_object_source_path(obj)
            if source_path and any(source_path.startswith(path) for path in SPECIFIED_PATHS):
                # 如果对象来自指定路径，则检查引用
                del obj

        # 调用 C 函数进行复杂的内存清理
        memory_cleaner.clean_memory()
        gc.collect()

        # 检查函数局部变量，清理不再被引用的变量
        local_vars = locals().copy()
        for var_name, var_value in local_vars.items():
            if var_name not in ('result', 'args', 'kwargs', 'weak_vars'):  # 排除结果和参数
                source_path = get_object_source_path(var_value)
                if source_path and any(source_path.startswith(path) for path in SPECIFIED_PATHS):
                    # 如果变量来自指定路径，则检查引用
                    if is_weakrefable(var_value):
                        weak_vars[var_name] = weakref.ref(var_value)
                        del var_value  # 删除强引用

        # 检查弱引用变量是否仍被引用
        for var_name, weak_ref in weak_vars.items():
            if weak_ref() is None:
                print(f"Python: 已清理未使用的变量: {var_name}")

        return result

    return wrapper
