# -*- coding: utf-8 -*-
from typing import Dict, Any

from common import logger


class TaskManager:
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}

    def add(self, task_control: Any, skip_ctx: Any, task_id: str) -> None:
        """
        Add task_control, skip_ctx, and task_id to the dictionary.

        :param task_control: An object that has a stop method.
        :param skip_ctx: An object that has a skip method.
        :param task_id: A string to be used as the key in the dictionary.
        """
        self.data[task_id] = {
            'task_control': task_control,
            'skip_ctx': skip_ctx
        }

    def force_stop(self, task_id: str) -> None:
        """
        Call the stop method of the corresponding task_control instance using the task_id.

        :param task_id: A string to be used as the key in the dictionary.
        """
        if task_id in self.data:
            task_control = self.data[task_id]['task_control']
            try:
                task_control.stop()
            except Exception as error:
                logger.error(error)
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def force_stop_all(self) -> None:
        """
        Call the stop method of all task_control instances in the dictionary.
        """
        for task_id, task_data in self.data.items():
            try:
                task_data['task_control'].stop()
            except Exception as error:
                logger.error(error)

    def remove(self, task_id: str) -> None:
        """
        Remove the specified task_id and its associated data from the dictionary.

        :param task_id: A string to be used as the key in the dictionary.
        """
        if task_id in self.data:
            del self.data[task_id]
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def check(self, task_id: str) -> bool:
        """
        Check if the given task_id exists in the dictionary.

        :param task_id: A string to be used as the key in the dictionary.
        :return: True if the task_id exists, otherwise False.
        """
        return task_id in self.data

    def skip_task(self, task_id: str) -> None:
        """
        Call the skip method of the corresponding skip_ctx instance using the task_id.

        :param task_id: A string to be used as the key in the dictionary.
        """
        if task_id in self.data:
            skip_ctx = self.data[task_id]['skip_ctx']
            try:
                skip_ctx.skip()
            except Exception as error:
                logger.error(error)
        else:
            logger.warning(f"No task found with task_id '{task_id}', operation invalid")

    def skip_all(self) -> None:
        """
        Call the skip method of all skip_ctx instances in the dictionary.
        """
        for task_id, task_data in self.data.items():
            try:
                task_data['skip_ctx'].skip()
            except Exception as error:
                logger.error(error)


# Create Manager instance
task_manager = TaskManager()