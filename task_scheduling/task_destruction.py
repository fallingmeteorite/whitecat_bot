from typing import Dict, Any

from common.logging import logger


class Manager:
    def __init__(self):
        self.data: Dict[str, Any] = {}

    def add(self, instance: Any, key: str) -> None:
        """
        将实例和键值对添加到字典中。

        :param instance: 实例化的类。
        :param key: 字符串，作为字典的键。
        """
        self.data[key] = instance
        logger.info(f"已添加实例 '{key}'")

    def stop(self, key: str) -> None:
        """
        通过键值调用对应实例的stop方法。

        :param key: 字符串，字典的键。
        """
        if key in self.data:
            instance = self.data[key]
            try:
                instance.stop()
                logger.warning(f"'{key}' 停止成功")
            except Exception as error:
                logger.error(error)
        else:
            logger.warning(f"没有发现对应的任务 '{key}', 操作无效")

    def stop_all(self) -> None:
        """
        调用字典中所有实例的stop方法。
        """
        for key, instance in self.data.items():
            try:
                instance.stop()
                logger.warning(f"'{key}' 停止成功")
            except Exception as error:
                logger.error(error)

    def remove(self, key: str) -> None:
        """
        从字典中删除指定的键值对。

        :param key: 字符串，字典的键。
        """
        if key in self.data:
            del self.data[key]
            logger.info(f"已删除任务 '{key}'")
        else:
            logger.warning(f"没有发现对应的任务 '{key}', 操作无效")


# 创建Manager实例
manager = Manager()
