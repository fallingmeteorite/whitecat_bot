# -*- coding: utf-8 -*-
from typing import Dict, Any

from common.logging import logger


class TaskManager:
    def __init__(self):
        self.data: Dict[str, Any] = {}

    def add(self, instance: Any, key: str) -> None:
        """
        Add an instance and its key-value pair to the dictionary.

        :param instance: The instantiated object.
        :param key: A string to be used as the key in the dictionary.
        """
        self.data[key] = instance

    def force_stop(self, key: str) -> None:
        """
        Call the stop method of the corresponding instance in the dictionary using the key.

        :param key: A string to be used as the key in the dictionary.
        """
        if key in self.data:
            instance = self.data[key]
            try:
                instance.stop()
                logger.warning(f" A stop command has been issued to the task '{key}'")
            except Exception as error:
                logger.error(error)
        else:
            logger.warning(f"No task found with key '{key}', operation invalid")

    def force_stop_all(self) -> None:
        """
        Call the stop method of all instances in the dictionary.
        """
        for key, instance in self.data.items():
            try:
                instance.stop()
                logger.warning(f"'{key}' stopped successfully")
            except Exception as error:
                logger.error(error)

    def remove(self, key: str) -> None:
        """
        Remove the specified key-value pair from the dictionary.

        :param key: A string to be used as the key in the dictionary.
        """
        if key in self.data:
            del self.data[key]
        else:
            logger.warning(f"No task found with key '{key}', operation invalid")

    def check(self, key: str) -> bool:
        """
        Check if the given key exists in the dictionary.

        :param key: A string to be used as the key in the dictionary.
        :return: True if the key exists, otherwise False.
        """
        return key in self.data


# Create Manager instance
task_manager = TaskManager()
