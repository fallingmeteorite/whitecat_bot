import importlib.util
import os
from typing import List, Optional, Tuple, Any

from common.config import config
from common.logging import logger


class AdapterManager:
    def __init__(self, message: Any):
        """
        初始化 AdapterManager。

        Args:
            message: 需要处理的消息。
        """
        self.message = message
        self.directory_path = config["adapter_dir"]
        self.adapters = self._load_adapters()  # 初始化时加载所有适配器

    def _load_module(self, module_path: str, module_name: str) -> Optional[Any]:
        """
        加载指定路径的模块。

        Args:
            module_path: 模块文件路径。
            module_name: 模块名称。

        Returns:
            Optional[Any]: 加载的模块对象，如果加载失败则返回 None。
        """
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                logger.warning(f"无法加载模块 {module_name}，路径 {module_path} 无效")
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"加载模块 {module_name} 失败: {e}")
            return None

    def _load_adapters(self) -> List[Any]:
        """
        加载指定目录下的所有适配器模块。

        Returns:
            List[Any]: 加载的适配器模块列表。
        """
        adapters = []
        for filename in os.listdir(self.directory_path):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # 去掉 '.py' 后缀
                module_path = os.path.join(self.directory_path, filename)
                module = self._load_module(module_path, module_name)
                if module is not None and hasattr(module, 'handle_message'):
                    adapters.append(module)
                    logger.debug(f"消息适配器已加载: ADAPTER| {module_name} |ADAPTER")
        return adapters

    def start(self) -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
        """
        运行所有适配器，直到某个适配器返回非 None 值。

        Returns:
            Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
            适配器返回的结果，如果所有适配器都返回 None，则返回 (None, None, None, None)。
        """
        for adapter in self.adapters:
            try:
                result = adapter.handle_message(self.message)
                if result is not None:
                    logger.debug(f"适配器 {adapter.__name__} 处理消息成功")
                    return result
            except Exception as e:
                logger.error(f"适配器 {adapter.__name__} 处理消息失败: {e}")
        return None, None, None, None
