import gc
import sys
import weakref
from typing import Set, Dict, Any, Optional

from common.logging import logger


class ModuleKeyRecorder:
    def __init__(self):
        """
        初始化模块记录器。
        """
        self.recording = False  # 是否正在记录
        self.initial_keys: Set[str] = set()  # 初始模块键集合
        self.recorded_data: Dict[str, Set[str]] = {}  # 记录的模块数据
        self.current_key: Optional[str] = None  # 当前记录的键

    def start_recording(self, import_param: str) -> None:
        """
        开始记录模块加载情况。

        Args:
            import_param: 导入参数，用于标识当前记录。
        """
        self.recording = True
        self.initial_keys = set(sys.modules.keys())
        self.current_key = import_param

        # 显式删除不再使用的变量
        del import_param

    def stop_recording(self) -> None:
        """
        停止记录模块加载情况，并保存新增的模块。
        """
        if not self.recording:
            return
        self.recording = False
        current_keys = set(sys.modules.keys())
        new_keys = current_keys - self.initial_keys
        self.recorded_data[self.current_key] = new_keys

        # 显式删除不再使用的变量
        del current_keys
        del new_keys

    def get_recorded_data(self) -> Dict[str, Set[str]]:
        """
        获取记录的数据。

        Returns:
            dict: 记录的模块数据。
        """
        data = self.recorded_data
        return data

    def remove_module_and_referencers(self, key: str) -> None:
        """
        移除指定键对应的模块及其引用者。

        Args:
            key: 要移除的键。
        """
        if key not in self.recorded_data:
            logger.debug(f"未找到对应的记录模块: '{key}'")
            return

        modules_to_remove = self.recorded_data[key]
        for module in modules_to_remove:
            if self._is_module_duplicate(module, key):
                logger.debug(f"模块 '{module}' 在其他记录中存在,无法删除")
                continue
            self._remove_module(module)

        del self.recorded_data[key]

        # 强制垃圾回收
        collected = gc.collect()
        logger.debug(f"垃圾回收完成，释放了 {collected} 个对象")

        # clear_all_free_lists()

        # 显式删除不再使用的变量
        del modules_to_remove

    def _is_module_duplicate(self, module: str, current_key: str) -> bool:
        """
        检查模块是否在其他记录中存在。

        Args:
            module: 要检查的模块。
            current_key: 当前记录的键。

        Returns:
            bool: 如果模块在其他记录中存在，返回 True；否则返回 False。
        """
        for key, modules in self.recorded_data.items():
            if key != current_key and module in modules:
                return True

        # 显式删除不再使用的变量
        del key
        del modules

        return False

    def _remove_module(self, module: str) -> None:
        """
        移除指定模块及其引用者。

        Args:
            module: 要移除的模块。
        """
        if module not in sys.modules:
            logger.debug(f"模块 '{module}' 不在 sys.modules 中，无法移除。")
            return

        # 获取模块的引用者并尝试移除
        referencers = gc.get_referrers(sys.modules[module])
        for ref in referencers:
            self._handle_referencer(ref, module)

        # 从 sys.modules 中移除模块
        try:
            del sys.modules[module]
        except:
            pass

        # 显式删除不再使用的变量
        del referencers

    def _handle_referencer(self, ref: Any, module: str) -> None:
        """
        处理引用者对象，尝试移除对模块的引用。

        Args:
            ref: 引用者对象。
            module: 要移除的模块。
        """
        try:
            if isinstance(ref, dict):
                ref.pop(module, None)  # 安全删除对应键
            elif isinstance(ref, list):
                ref[:] = [item for item in ref if item != module]
            elif isinstance(ref, weakref.ProxyType):
                ref._remove(module)  # 删除弱引用
            elif isinstance(ref, type):
                pass
            elif callable(ref):
                weak_ref = weakref.ref(ref)
                weak_ref()  # 触发引用的释放
        except Exception as e:
            logger.debug(f"处理引用者时发生错误: {e}")

        # 显式删除不再使用的变量
        del ref
        del module


# 全局实例
recorder = ModuleKeyRecorder()
