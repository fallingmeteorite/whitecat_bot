import ctypes
import functools
import gc
import os
import sys
import weakref
from typing import Callable, Any, Dict

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


def memory_release_decorator(func: Callable) -> Callable:
    """
    内存释放装饰器，用于检查并清理不再被引用的模块和变量。
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

        # 使用弱引用检查模块是否仍被引用
        for module_name in new_modules:
            module = sys.modules[module_name]
            if is_weakrefable(module):
                weak_ref = weakref.ref(module)
                del module  # 删除强引用

                # 如果弱引用返回 None，说明模块没有被其他对象引用
                if weak_ref() is None:
                    del sys.modules[module_name]  # 从 sys.modules 中移除
                    print(f"Python: 已卸载未使用的模块: {module_name}")

        # 检查函数局部变量，清理不再被引用的变量
        local_vars = locals().copy()
        for var_name, var_value in local_vars.items():
            if var_name not in ('result', 'args', 'kwargs', 'weak_vars'):  # 排除结果和参数
                if is_weakrefable(var_value):
                    weak_vars[var_name] = weakref.ref(var_value)
                    del var_value  # 删除强引用

        # 检查弱引用变量是否仍被引用
        for var_name, weak_ref in weak_vars.items():
            if weak_ref() is None:
                print(f"Python: 已清理未使用的变量: {var_name}")

        # 调用 C 函数进行复杂的内存清理
        memory_cleaner.clean_memory()
        print(f"Python: 释放了 {gc.collect()} 字节的内存")

        return result

    return wrapper
