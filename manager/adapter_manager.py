from typing import Optional, Tuple, Any, Dict, Callable

from common.config import config
from common.logging import logger
from module_manager.plugins_load import load


class AdapterManager:
    __slots__ = ['adapter_info']
    """
    适配理器类，负责规范消息输出。
    """

    def __init__(self):
        """
        初始化适配管理器，创建核心字典 `adapter_info` 用于存储适配处理函数。
        """
        self.adapter_info: Dict[str, Callable] = {}

    def register_plugin(self, name: str, handler: Callable) -> None:
        """
        注册适配处理插件。

        Args:
            name: 文件名称。
            handler: 文件处理函数。

        Raises:
            ValueError: 如果 `handler` 不是可调用对象。
        """
        if not callable(handler):
            raise ValueError("Handler must be a callable function.")
        self.adapter_info[name] = handler
        logger.debug(f"ADAPTER 适配器:| {name} |导入成功 ADAPTER|")

    def handle_command(self, message: Any) -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
        """
        运行所有适配器，直到某个适配器返回非 None 值。

        Args:
            message: 需要处理的消息。

        Returns:
            Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
            适配器返回的结果，如果所有适配器都返回 None，则返回 (None, None, None, None)。
        """

        for adapter_name, adapter_func in self.adapter_info.items():
            try:
                result = adapter_func(message)
                if result is not None:
                    logger.debug(f"适配器| {adapter_name} |处理消息成功")
                    return result
            except Exception as e:
                logger.error(f"适配器| {adapter_name} |处理消息失败: {e}")
        return None, None, None, None


# 加载文件管理器
adapter_dir = config["adapter_dir"]
adapter_manager, load_module = load(adapter_dir, AdapterManager)
del load_module
