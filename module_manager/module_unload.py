import gc
import os
import sys
from typing import List, Set, Optional

from common.logging import logger
from core.memory_release import memory_release_decorator

def find_project_root(start_path: Optional[str] = None) -> Optional[str]:
    """查找项目根目录"""
    if start_path is None:
        start_path = os.getcwd()

    current_path = start_path
    while current_path != os.path.dirname(current_path):
        # 检查是否存在常见的项目根目录标志文件或目录
        if any(os.path.exists(os.path.join(current_path, marker)) for marker in ['app.py']):
            return current_path
        current_path = os.path.dirname(current_path)

    return None


def is_standard_library_file(file_path: Optional[str]) -> bool:
    """检查文件是否位于 Python 标准库路径中"""
    if not file_path:
        return False
    stdlib_path = os.path.join(sys.prefix, 'lib')
    return file_path.startswith(stdlib_path)


def is_in_project_root(file_path: Optional[str], project_root: Optional[str]) -> bool:
    """检查文件是否位于项目根目录中"""
    if not file_path or not project_root:
        return False
    return file_path.startswith(project_root)


def get_module_importers(module_name: str) -> List[str]:
    """获取导入指定模块的所有非标准库文件，并且这些文件位于项目根目录中"""
    importers: Set[str] = set()
    project_root = find_project_root()

    for module in sys.modules.values():
        if not hasattr(module, '__dict__'):
            continue
        if module_name in module.__dict__:
            if hasattr(module, '__file__') and module.__file__:
                file_path = module.__file__
                if not is_standard_library_file(file_path) and is_in_project_root(file_path, project_root):
                    importers.add(os.path.basename(file_path))
    return list(importers)


def remove_module_reference(module_name: str, file_name: str) -> None:
    """移除指定模块在某个文件中的引用"""
    for module in sys.modules.values():
        if not hasattr(module, '__dict__'):
            continue
        if module_name in module.__dict__:
            if hasattr(module, '__file__') and module.__file__:
                if os.path.basename(module.__file__) == file_name:
                    del module.__dict__[module_name]
                    logger.warning(f"已移除模块 '{module_name}' 在文件 '{file_name}' 中的引用")


def module_in_use(module_name: str) -> int:
    """检查模块是否正在被使用"""
    if module_name not in sys.modules:
        return False
    module = sys.modules[module_name]
    # 排除模块自身的引用
    return len(gc.get_referrers(module))


def _clean_module(module_name: str) -> None:
    """清理模块的全局变量和引用"""
    module = sys.modules[module_name]
    # 清理全局变量
    for var_name in list(module.__dict__.keys()):
        if var_name not in globals() and var_name not in locals():
            del module.__dict__[var_name]
    # 清理模块引用
    for referrer in gc.get_referrers(module):
        if referrer is not module:
            del referrer
    del sys.modules[module_name]

@memory_release_decorator
def force_unload_unused_modules(module_names: List[str]) -> None:
    """强制卸载未使用的模块"""
    unloaded_modules: List[str] = []
    for module_name in module_names:
        if module_name not in sys.modules:
            continue

        # 检查模块是否被其他非标准库文件引用
        # 检查模块是否正在被使用
        if module_in_use(module_name) > 2 and get_module_importers(module_name):
            continue

        # 清理模块
        _clean_module(module_name)
        unloaded_modules.append(module_name)

    logger.info(f"卸载模块为: {unloaded_modules}")
    logger.info(f"已加载模块数: {len(sys.modules)}")
