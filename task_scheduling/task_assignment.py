# -*- coding: utf-8 -*-
import uuid
from typing import Callable

from common.logging import logger
from .scheduler import io_async_task, io_liner_task
from .scheduler.utils import is_async_function


def add_task(timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> str or None:
    """
    Add a task to the queue, choosing between asynchronous or linear tasks based on the function type.
    Generates a unique task ID and returns it.

    :param timeout_processing: Whether to enable timeout processing.
    :param task_name: Task name.
    :param func: Task function.
    :param args: Positional arguments for the task function.
    :param kwargs: Keyword arguments for the task function.
    :return: Unique task ID.
    """
    # Check if func is actually a function
    if not callable(func):
        logger.warning("The provided func is not a callable function")
        return None

    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    if is_async_function(func):
        # Run asynchronous task
        state = io_async_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)
        if state:
            logger.info(f"Io asyncio task | {task_id} | added successfully")

    else:
        # Run linear task
        state = io_liner_task.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)
        if state:
            logger.info(f"Io linear task | {task_id} | added successfully")

    if not state:
        logger.info(f"Task | {task_id} | added failed")

    return task_id if state else None


def shutdown(force_cleanup: bool) -> None:
    """
    :param force_cleanup: Force the end of a running task

    Shutdown the scheduler, stop all tasks, and release resources.
    Only checks if the scheduler is running and forces a shutdown if necessary.
    """
    # Shutdown asynchronous task scheduler if running
    if hasattr(io_async_task, "scheduler_started") and io_async_task.scheduler_started:
        logger.info("Detected io asyncio task scheduler is running, shutting down...")
        io_async_task.stop_all_schedulers(force_cleanup)
        logger.info("Io asyncio task scheduler has been shut down.")

    # Shutdown linear task scheduler if running
    if hasattr(io_liner_task, "scheduler_started") and io_liner_task.scheduler_started:
        logger.info("Detected io linear task scheduler is running, shutting down...")
        io_liner_task.stop_scheduler(force_cleanup)
        logger.info("Io linear task scheduler has been shut down.")

    logger.info("All scheduler has been shut down.")

