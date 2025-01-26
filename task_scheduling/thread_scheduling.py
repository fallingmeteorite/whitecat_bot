# -*- coding: utf-8 -*-
import inspect
import uuid
from typing import Callable

from common.logging import logger
from .scheduler.asyn_task_assignment import asyntask
from .scheduler.line_task_assignment import linetask


def is_async_function(func: Callable) -> bool:
    """
    Determine if a function is an asynchronous function.

    :param func: The function to check.
    :return: True if the function is asynchronous; otherwise, False.
    """
    return inspect.iscoroutinefunction(func)


def add_task(timeout_processing: bool, task_name: str, func: Callable, *args, **kwargs) -> str or None:
    """
    Add a task to the queue, choosing between asynchronous or linear tasks based on the function type.
    Generates a unique task ID and returns it.

    :param timeout_processing: Whether to enable timeout processing.
    :param task_name: task name
    :param func: Task function.
    :param args: Positional arguments for the task function.
    :param kwargs: Keyword arguments for the task function.
    :return: Unique task ID.
    """
    # Check if func is actually a function
    if not callable(func):
        logger.warning(f"The provided func is not a callable function")
        return None

    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    if is_async_function(func):
        # Run asynchronous task
        state = asyntask.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)
    else:
        # Run linear task
        state = linetask.add_task(timeout_processing, task_name, task_id, func, *args, **kwargs)

    if state:
        logger.info(f"Task added with ID: {task_id}")
        return task_id
    else:
        logger.info(f"Failed to add a task: {task_id}")
        return None


def shutdown(force_cleanup: bool) -> None:
    """
    :param force_cleanup: Force the end of a running task

    Shutdown the scheduler, stop all tasks, and release resources.
    Only checks if the scheduler is running and forces a shutdown if necessary.
    """
    # Shutdown asynchronous task scheduler if running
    if hasattr(asyntask, "scheduler_started") and asyntask.scheduler_started:
        logger.info("Detected asynchronous task scheduler is running, shutting down...")
        asyntask.stop_scheduler(force_cleanup)
        logger.info("Asynchronous task scheduler has been shut down.")

    # Shutdown linear task scheduler if running
    if hasattr(linetask, "scheduler_started") and linetask.scheduler_started:
        logger.info("Detected linear task scheduler is running, shutting down...")
        linetask.stop_scheduler(force_cleanup)
        logger.info("Linear task scheduler has been shut down.")

    logger.info("All schedulers have been shut down, resources have been released.")
