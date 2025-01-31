# -*- coding: utf-8 -*-
import time
from typing import Dict, List

from config import config
from .scheduler import io_async_task
from .scheduler import io_liner_task


def format_task_info(task_id: str, details: Dict, show_id: bool) -> str:
    """
    Format task information.

    :param task_id: Task ID.
    :param details: Task details.
    :param show_id: Boolean flag to determine whether to show the task ID.
    :return: Formatted task information.
    """
    elapsed_time_display = "NaN"
    task_name = details.get("task_name", "Unknown")  # Get task name, default to "Unknown" if not provided
    start_time = details.get("start_time", 0)
    end_time = details.get("end_time", 0)
    status = details.get("status", "unknown")

    # Calculate elapsed time
    if status == "pending":
        pass

    if status == "completed":
        elapsed_time = max(end_time - start_time, 0)
        if not elapsed_time > config["watch_dog_time"]:
            elapsed_time_display = f"{elapsed_time:.2f}"

    if status == "failed":
        elapsed_time = max(end_time - start_time, 0)
        if not elapsed_time > config["watch_dog_time"]:
            elapsed_time_display = f"{elapsed_time:.2f}"

    if status == "running":
        current_time = time.time()
        elapsed_time = max(current_time - start_time, 0)
        if not elapsed_time > config["watch_dog_time"]:
            elapsed_time_display = f"{elapsed_time:.2f}"

    # Add special hints based on status
    status_hint = {
        "timeout": " (Task timed out)",
        "failed": " (Task failed)",
        "cancelled": " (Task cancelled)",
    }.get(status, "")

    # Format task information
    if show_id:
        return f"Name: {task_name}, ID: {task_id}, Status: {status}{status_hint}, Elapsed Time: {elapsed_time_display} seconds\n"
    else:
        return f"Name: {task_name}, Status: {status}{status_hint}, Elapsed Time: {elapsed_time_display} seconds\n"


def get_queue_info_string(task_queue, queue_type: str, show_id: bool) -> str:
    """
    Get the string of queue information.

    :param task_queue: Task queue object.
    :param queue_type: Queue type (e.g., "line" or "asyncio").
    :param show_id: Boolean flag to determine whether to show the task ID.
    :return: String of queue information.
    """
    try:
        queue_info = task_queue.get_queue_info()
        info: List[str] = [
            f"\n{queue_type} queue size: {queue_info['queue_size']}, ",
            f"Running tasks count: {queue_info['running_tasks_count']}, ",
            f"Failed tasks count: {queue_info['failed_tasks_count']}\n",
        ]

        # Output task details
        for task_id, details in queue_info['task_details'].items():
            # if details["status"] != "pending":
            info.append(format_task_info(task_id, details, show_id))

        if queue_info.get("error_logs"):
            info.append(f"\n{queue_type} error logs:\n")
            for error in queue_info["error_logs"]:
                info.append(
                    f"Task ID: {error['task_id']}, Error time: {error['error_time']}, "
                    f"Error message: {error['error_message']}\n"
                )

        return "".join(info)

    except Exception as e:
        return f"Error occurred while getting {queue_type} queue information: {e}\n"


def get_all_queue_info(queue_type: str, show_id: bool) -> str:
    """
    Get the string of all queue information.

    :param queue_type: Queue type (e.g., "line" or "asyncio").
    :param show_id: Boolean flag to determine whether to show the task ID.
    :return: String of all queue information.
    """
    queue_mapping = {
        "line": io_liner_task,
        "asyncio": io_async_task,
    }

    task_queue = queue_mapping.get(queue_type)
    if task_queue:
        return get_queue_info_string(task_queue, queue_type, show_id)
    else:
        return f"Unknown queue type: {queue_type}"
