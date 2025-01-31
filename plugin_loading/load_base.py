import ast
import gc
import os
import sys
import types
import weakref
from typing import Set

from common import logger


class SimpleModuleLoader:
    def __init__(self, module_name: str, module_path: str) -> None:
        """
        初始化模块加载器。

        :param module_name: 模块名称
        :param module_path: 模块文件路径
        """
        self.module_name = module_name
        self.module_path = os.path.abspath(module_path)  # 使用绝对路径
        self.imported_modules: Set[str] = set()  # 用于存储导入的模块

    def load_module(self) -> types.ModuleType:
        """
        加载模块。

        :return: 加载的模块对象
        """
        # 检查模块是否已经加载
        if self.module_name in sys.modules:
            logger.debug(f"模块 '{self.module_name}' 已加载，直接返回")
            return sys.modules[self.module_name]

        # 检查模块文件是否存在
        if not os.path.exists(self.module_path):
            raise ImportError(f"模块文件不存在: {self.module_path}")

        # 读取模块文件内容
        with open(self.module_path, "r", encoding="utf-8") as f:
            module_code = f.read()

        # 解析模块代码，查找导入语句
        self._parse_imports(module_code)

        # 创建模块对象
        module = types.ModuleType(self.module_name)
        module.__file__ = self.module_path
        module.__package__ = ""
        module.__name__ = self.module_name
        module.__loader__ = weakref.ref(self)()  # 使用弱引用设置加载器为当前对象

        # 将模块添加到 sys.modules
        sys.modules[self.module_name] = module

        # 编译并执行模块代码
        compiled_code = compile(module_code, self.module_path, "exec")

        try:
            exec(compiled_code, module.__dict__)
        except Exception as error:
            logger.error(error)

        logger.debug(f"模块 '{self.module_name}' 加载成功")
        return module

    def _parse_imports(self, module_code: str) -> None:
        """
        解析模块代码，查找导入语句并标记。

        :param module_code: 模块代码
        """
        tree = ast.parse(module_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imported_modules.add(node.module)

        # 显式删除不再使用的变量
        del tree
        del node

    def unload_module(self, module: types.ModuleType) -> None:
        """
        卸载模块并强制清理内存。

        :param module: 要卸载的模块对象
        :raises TypeError: 如果提供的参数不是模块对象
        """
        if not isinstance(module, types.ModuleType):
            raise TypeError("参数必须是一个模块对象。")

        # 获取模块名称
        module_name = module.__name__

        # 遍历 module.__dict__ 中的属性，查找并卸载所有相关模块
        for attr in list(module.__dict__):
            attr_value = module.__dict__[attr]

            # 如果属性是一个模块，递归卸载
            if isinstance(attr_value, types.ModuleType):
                self.unload_module(attr_value)

        # 从 sys.modules 中移除模块
        if module_name in sys.modules:
            del sys.modules[module_name]
            logger.debug(f"模块 '{module_name}' 已从 sys.modules 中移除")

            # 清理导入的模块
            for imported_module in self.imported_modules:
                if imported_module in sys.modules:
                    del sys.modules[imported_module]
                    logger.debug(f"导入的模块 '{imported_module}' 已从 sys.modules 中移除")

            # 清空模块的 __dict__
            module.__dict__.clear()
            logger.debug(f"模块 '{module_name}' 的 __dict__ 已清空")

            # 强制垃圾回收
            collected = gc.collect()
            logger.debug(f"垃圾回收完成，释放了 {collected} 个对象")

            # 确保内存归还操作系统
            self._release_memory_to_os()
        else:
            logger.debug(f"模块 '{module_name}' 未加载，无需卸载")

    @staticmethod
    def _release_memory_to_os() -> None:
        """
        尝试将内存归还给操作系统。
        """
        # 调用 gc.collect() 确保所有可回收对象都被清理
        gc.collect()

        logger.debug("尝试将内存归还给操作系统")
