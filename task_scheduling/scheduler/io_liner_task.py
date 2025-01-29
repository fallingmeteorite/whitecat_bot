# -*- coding: utf-8 -*-
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from functools import partial
from typing import Callable, Dict, List, Tuple, Optional, Any

from task_scheduling.scheduler.task_management import task_manager
from config.config import config
from common.logging import logger
from memory_management.memory_release import memory_release_decorator
from ..stopit.force_thread_stop import skip_on_demand, StopException
from ..stopit.threadstop import ThreadingTimeout, TimeoutException


class IoLinerTask:
    """
    Linear task manager class, responsible for managing the scheduling, execution, and monitoring of linear tasks.
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'task_details', 'lock', 'condition', 'scheduler_lock',
        'scheduler_started', 'scheduler_stop_event', 'error_logs', 'scheduler_thread',
        'banned_task_names', 'idle_timer', 'idle_timeout', 'idle_timer_lock', 'task_results'
    ]

    def __init__(self) -> None:
        self.task_queue = queue.Queue()  # Task queue
        self.running_tasks = {}  # Running tasks
        self.task_details: Dict[str, Dict] = {}  # Task details
        self.lock = threading.Lock()  # Lock to protect access to shared resources
        self.scheduler_lock = threading.RLock()  # Thread unlock

        self.condition = threading.Condition()  # Condition variable for thread synchronization
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.error_logs: List[Dict] = []  # Logs, keep up to 10
        self.scheduler_thread: Optional[threading.Thread] = None  # Scheduler thread
        self.banned_task_names: List[str] = []  # List of banned task names
        self.idle_timer: Optional[threading.Timer] = None  # Idle timer
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID

    # Add the task to the scheduler
    def add_task(self, timeout_processing: bool, task_name: str, task_id: str, func: Callable, *args, **kwargs) -> bool:
        """
        Add a task to the task queue.

        :param timeout_processing: Whether to enable timeout processing.
        :param task_name: Task name (can be repeated).
        :param task_id: Task ID (must be unique).
        :param func: Task function.
        :param args: Positional arguments for the task function.
        :param kwargs: Keyword arguments for the task function.
        :return: True if the task was successfully added, False otherwise.
        """
        try:
            with self.scheduler_lock:
                # Check if the task is banned
                if task_name in self.banned_task_names:
                    logger.warning(f"Io linear task | {task_id} | is banned and will be deleted")
                    return False

                # Check if the queue is full
                if self.task_queue.qsize() >= config["maximum_queue_line"]:
                    logger.warning(f"Io linear task | {task_id} | not added, queue is full")
                    return False

                # Check if the scheduler is stopping due to idle timeout
                if self.scheduler_stop_event.is_set() and not self.scheduler_started:
                    # Wait for the scheduler thread to fully stop
                    self._join_scheduler_thread()
                    logger.info("Scheduler has fully stopped")

                # Add the task to the queue
                with self.lock:
                    self.task_details[task_id] = {
                        "task_name": task_name,
                        "start_time": None,
                        "status": "pending"
                    }
                self.task_queue.put((timeout_processing, task_name, task_id, func, args, kwargs))

                if not self.scheduler_started:
                    self._start_scheduler()

                # Notify the scheduler thread
                with self.condition:
                    self.condition.notify()

                # Cancel the idle timer
                self._cancel_idle_timer()
                return True
        except Exception as e:
            logger.error(f"Io linear task | {task_id} | error adding task: {e}")
            return False

    # Start the scheduler
    def _start_scheduler(self) -> None:
        """
        Start the scheduler thread.
        """
        self.scheduler_started = True
        self.scheduler_thread = threading.Thread(target=self._scheduler, daemon=True)
        self.scheduler_thread.start()

    # Stop the scheduler
    def stop_scheduler(self, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        Stop the scheduler thread.

        :param force_cleanup: If True, force stop all tasks and clear the queue.
                              If False, gracefully stop the scheduler (e.g., due to idle timeout).
        :param system_operations: System execution metrics
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not self.task_queue.empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Io linear task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")

            if force_cleanup:
                logger.warning("Force stopping scheduler and cleaning up tasks")
                # Force stop all running tasks
                task_manager.force_stop_all()
                task_manager.skip_all()
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue()

            # Notify all waiting threads
            with self.condition:
                self.condition.notify_all()

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread()

            # Reset state variables
            self.scheduler_started = False
            self.scheduler_stop_event.clear()
            self.error_logs = []
            self.scheduler_thread = None
            self.banned_task_names = []
            self.idle_timer = None
            self.task_results = {}

            logger.info(
                "Scheduler and event loop have stopped, all resources have been released and parameters reset")

    # Task scheduler
    def _scheduler(self) -> None:
        """
        Scheduler function, fetch tasks from the task queue and submit them to the thread pool for execution.
        """
        with ThreadPoolExecutor(max_workers=int(config["line_task_max"])) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        continue

                    task = self.task_queue.get()

                timeout_processing, task_name, task_id, func, args, kwargs = task

                with self.lock:
                    if task_name in [details[1] for details in self.running_tasks.values()]:
                        self.task_queue.put(task)
                        continue

                    future = executor.submit(self._execute_task, task)
                    self.running_tasks[task_id] = [future, task_name]

                future.add_done_callback(partial(self._task_done, task_id))

    # A function that executes a task
    @memory_release_decorator
    def _execute_task(self, task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
        """
        Execute a linear task.

        :param task: Task tuple, including timeout processing flag, task name, task ID, task function, positional arguments, and keyword arguments.
        """
        timeout_processing, task_name, task_id, func, args, kwargs = task

        try:
            with self.lock:
                # Modify the task status
                self.task_details[task_id]["start_time"] = time.time()
                self.task_details[task_id]["status"] = "running"

            logger.info(f"Start running io linear task, task ID: {task_id}")
            if timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False) as task_control:
                    with skip_on_demand() as skip_ctx:
                        task_manager.add(task_control, skip_ctx, task_id)
                        return_results = func(*args, **kwargs)
                    task_manager.remove(task_id)
            else:
                with ThreadingTimeout(seconds=None, swallow_exc=False) as task_control:
                    with skip_on_demand() as skip_ctx:
                        task_manager.add(task_control, skip_ctx, task_id)
                        return_results = func(*args, **kwargs)
                    task_manager.remove(task_id)
        except TimeoutException:
            logger.warning(f"Io linear task | {task_id} | timed out, forced termination")
            self._update_task_status(task_id, "timeout")
            raise  # Re-raise the exception to be handled by the task_done callback
        except StopException:
            logger.warning(f"Io linear task | {task_id} | timed out, forced termination")
            self._update_task_status(task_id, "timeout")
            raise  # Re-raise the exception to be handled by the task_done callback
        except Exception as e:
            logger.error(f"Io linear task | {task_id} | execution failed: {e}")
            self._log_error(task_id, e)
            raise  # Re-raise the exception to be handled by the task_done callback
        finally:
            if task_manager.check(task_id):
                task_manager.remove(task_id)
                # Define variables when they are not defined
                return_results = "error happened"
                return return_results
            else:
                return return_results

    def _task_done(self, task_id: str, future: Future) -> None:
        """
        Callback function after a task is completed.

        :param task_id: Task ID.
        :param future: Future object corresponding to the task.
        """
        try:
            result = future.result()  # Get task result, exceptions will be raised here

            # Store task return results, keep up to 2 results
            with self.lock:
                if task_id not in self.task_results:
                    self.task_results[task_id] = []
                self.task_results[task_id].append(result)
                if len(self.task_results[task_id]) > 2:
                    self.task_results[task_id].pop(0)  # Remove the oldest result
            if not result == "error happened":
                self._update_task_status(task_id, "completed")

        except TimeoutException as e:
            logger.error(f"Io linear task | {task_id} | timed out: {e}")
            self._update_task_status(task_id, "timeout")
            self._log_error(task_id, e)
        except Exception as e:
            logger.error(f"Io linear task | {task_id} | execution failed: {e}")
            self._update_task_status(task_id, "failed")
            self._log_error(task_id, e)
        finally:
            # Ensure the Future object is deleted
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

            # Check if all tasks are completed
            with self.lock:
                if self.task_queue.empty() and len(self.running_tasks) == 0:
                    self._reset_idle_timer()

            # Check the number of task information
            self._check_and_log_task_details()

    # Update the task status
    def _update_task_status(self, task_id: str, status: str) -> None:
        """
        Update task status.

        :param task_id: Task ID.
        :param status: Task status.
        """
        with self.lock:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.task_details:
                self.task_details[task_id]["status"] = status
                # Set end_time to NaN if the task failed because of timeout and timeout_processing was False
                if status == "timeout":
                    self.task_details[task_id]["end_time"] = "NaN"
                else:
                    self.task_details[task_id]["end_time"] = time.time()

    def _log_error(self, task_id: str, exception: Exception) -> None:
        """
        Log error information during task execution.

        :param task_id: Task ID.
        :param exception: Exception object.
        """
        error_info = {
            "task_id": task_id,
            "error_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "error_message": str(exception)
        }
        with self.lock:
            self.error_logs.append(error_info)
            if len(self.error_logs) > 10:
                self.error_logs.pop(0)  # Remove the oldest error log

    # The task scheduler closes the countdown
    def _reset_idle_timer(self) -> None:
        """
        Reset the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
            self.idle_timer = threading.Timer(self.idle_timeout, self.stop_scheduler, args=(False, True,))
            self.idle_timer.start()

    def _cancel_idle_timer(self) -> None:
        """
        Cancel the idle timer.
        """
        with self.idle_timer_lock:
            if self.idle_timer is not None:
                self.idle_timer.cancel()
                self.idle_timer = None

    def _clear_task_queue(self) -> None:
        """
        Clear the task queue.
        """
        while not self.task_queue.empty():
            self.task_queue.get()

    def _join_scheduler_thread(self) -> None:
        """
        Wait for the scheduler thread to finish.
        """
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join()

    def get_queue_info(self) -> Dict:
        """
        Get detailed information about the task queue.

        Returns:
            Dict: Dictionary containing queue size, number of running tasks, number of failed tasks, task details, and error logs.
        """
        with self.condition:
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": 0,
                "failed_tasks_count": 0,
                "task_details": {},
                "error_logs": self.error_logs.copy()  # Return recent error logs
            }

            for task_id, details in self.task_details.items():
                status = details.get("status")
                task_name = details.get("task_name", "Unknown")
                if status == "running":
                    start_time = details.get("start_time")
                    current_time = time.time()
                    if current_time - start_time > config["watch_dog_time"]:
                        # Change end time of timed out tasks to NaN
                        queue_info["task_details"][task_id] = {
                            "task_name": task_name,
                            "start_time": start_time,
                            "status": status,
                            "end_time": "NaN"
                        }
                    else:
                        queue_info["task_details"][task_id] = details
                    queue_info["running_tasks_count"] += 1
                elif status == "failed":
                    queue_info["task_details"][task_id] = details
                    queue_info["failed_tasks_count"] += 1
                else:
                    queue_info["task_details"][task_id] = details

        return queue_info

    def force_stop_task(self, task_id: str) -> None:
        """
        Force stop a task by its task ID.

        :param task_id: task ID.
        """
        with self.lock:
            if task_id not in self.running_tasks:
                logger.warning(f"Io linear task | {task_id} | does not exist or is already completed")
                return
            task_manager.force_stop(task_id)
            task_manager.skip_task(task_id)
            task_manager.remove(task_id)
            logger.warning(f"Io linear task | {task_id} | has been forcibly cancelled")
        # Due to the influence of the lock, it is unlocked first
        self._update_task_status(task_id, "cancelled")

        with self.lock:
            # Clean up task details and results
            if task_id in self.task_details:
                del self.task_details[task_id]
            if task_id in self.task_results:
                del self.task_results[task_id]

    def cancel_all_queued_tasks_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the same name.

        :param task_name: Task name.
        """
        with self.condition:
            temp_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task[1] == task_name:  # Use function name to match task name
                    logger.warning(
                        f"Io linear task | {task_name} | is waiting to be executed in the queue, has been deleted")
                else:
                    temp_queue.put(task)

            # Put uncancelled tasks back into the queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get())

    def ban_task_name(self, task_name: str) -> None:
        """
        Ban a task name from execution, delete tasks directly if detected and print information.

        :param task_name: Task name.
        """
        with self.lock:
            self.banned_task_names.append(task_name)
            logger.warning(f"Io linear task | {task_name} | is banned from execution")

            # Cancel all queued tasks with the banned task name
            self.cancel_all_queued_tasks_by_name(task_name)

    def allow_task_name(self, task_name: str) -> None:
        """
        Allow a banned task name to be executed again.

        :param task_name: Task name.
        """
        with self.lock:
            if task_name in self.banned_task_names:
                self.banned_task_names.remove(task_name)
                logger.info(f"Io linear task | {task_name} | is allowed for execution")
            else:
                logger.warning(f"Io linear task | {task_name} | is not banned, no action taken")

    # Obtain the information returned by the corresponding task
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        if task_id in self.task_results and self.task_results[task_id]:
            result = self.task_results[task_id].pop(0)  # Return and delete the oldest result
            with self.lock:
                if not self.task_results[task_id]:
                    del self.task_results[task_id]
            return result
        return None

    def _check_and_log_task_details(self) -> None:
        """
        Check if the number of task details exceeds the configured limit and remove those with specific statuses.
        """
        with self.lock:
            task_details_copy = self.task_details.copy()
            if len(task_details_copy) > config["maximum_task_info_storage"]:
                logger.info(f"More than {config['maximum_task_info_storage']} task details detected. "
                            f"Cleaning up old task details.")

                # Filter out tasks with status 'failed', 'completed', or 'timeout'
                new_task_details = {task_id: details for task_id, details in task_details_copy.items()
                                    if details.get("status") not in ["failed", "completed", "timeout"]}

                # Update the task details with the filtered results
                self.task_details = new_task_details

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Obtain task status information for a specified task_id.

        :param task_id: Task ID.
        :return: A dictionary containing information about the status of the task, or None if the task does not exist.
        """
        if task_id in self.task_details:
            return self.task_details[task_id]
        logger.warning(f"Io linear task | {task_id} | does not exist or has been completed and removed")
        return None


# Instantiate object
io_liner_task = IoLinerTask()
