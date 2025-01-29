# -*- coding: utf-8 -*-
import asyncio
import queue
import threading
import time
from typing import Dict, List, Tuple, Callable, Optional, Any

from common.logging import logger
from config.config import config
from memory_management.memory_release import memory_release_decorator
from ..stopit.threadstop import ThreadingTimeout, TimeoutException


class IoAsyncTask:
    """
    Asynchronous task manager class, responsible for scheduling, executing, and monitoring asynchronous tasks.
    """
    __slots__ = [
        'task_queues', 'condition', 'scheduler_lock', 'scheduler_started', 'scheduler_stop_event',
        'task_details', 'running_tasks', 'error_logs', 'scheduler_threads', 'event_loops',
        'banned_task_ids', 'idle_timers', 'idle_timeout', 'idle_timer_lock', 'task_results',
        'task_counters'
    ]

    def __init__(self) -> None:
        """
        Initialize the asynchronous task manager.
        """
        self.task_queues: Dict[str, queue.Queue] = {}  # Task queues for each task name
        self.condition = threading.Condition()  # Condition variable for thread synchronization
        self.scheduler_lock = threading.RLock()  # Thread unlock
        self.scheduler_started = False  # Whether the scheduler thread has started
        self.scheduler_stop_event = threading.Event()  # Scheduler thread stop event
        self.task_details: Dict[str, Dict] = {}  # Details of tasks
        self.running_tasks: Dict[str, list[Any]] = {}  # Use weak references to reduce memory usage
        self.error_logs: List[Dict] = []  # Error logs, keep up to 10
        self.scheduler_threads: Dict[str, threading.Thread] = {}  # Scheduler threads for each task name
        self.event_loops: Dict[str, asyncio.AbstractEventLoop] = {}  # Event loops for each task name
        self.banned_task_ids: List[str] = []  # List of task IDs to be banned
        self.idle_timers: Dict[str, threading.Timer] = {}  # Idle timers for each task name
        self.idle_timeout = config["max_idle_time"]  # Idle timeout, default is 60 seconds
        self.idle_timer_lock = threading.Lock()  # Idle timer lock
        self.task_results: Dict[str, List[Any]] = {}  # Store task return results, keep up to 2 results for each task ID
        self.task_counters: Dict[str, int] = {}  # Used to track the number of tasks being executed in each event loop

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
        """
        try:
            with self.scheduler_lock:
                if task_name in self.banned_task_ids:
                    logger.warning(f"Io asyncio task | {task_id} | is banned and will be deleted")
                    return False

                if task_name not in self.task_queues:
                    self.task_queues[task_name] = queue.Queue()

                if self.task_queues[task_name].qsize() >= config["maximum_queue_async"]:
                    logger.warning(f"Io asyncio task | {task_id} | not added, queue is full")
                    logger.warning(f"Asyncio queue is full!!!")
                    return False

                with self.condition:
                    # Store task name in task_details
                    self.task_details[task_id] = {
                        "task_name": task_name,
                        "start_time": None,
                        "status": "pending"
                    }

                self.task_queues[task_name].put((timeout_processing, task_name, task_id, func, args, kwargs))

                # If the scheduler thread has not started, start it
                if task_name not in self.scheduler_threads or not self.scheduler_threads[task_name].is_alive():
                    self.event_loops[task_name] = asyncio.new_event_loop()
                    self.task_counters[task_name] = 0  # Initialize the task counter
                    self._start_scheduler(task_name)

                # Cancel the idle timer
                self._cancel_idle_timer(task_name)

                with self.condition:
                    self.condition.notify()  # Notify the scheduler thread that a new task is available

                return True
        except Exception as e:
            logger.error(f"Error adding task | {task_id} |: {e}")
            return False

    # Start the scheduler
    def _start_scheduler(self, task_name: str) -> None:
        """
        Start the scheduler thread and the event loop thread for a specific task name.

        :param task_name: Task name.
        """
        with self.condition:
            if task_name not in self.scheduler_threads or not self.scheduler_threads[task_name].is_alive():
                self.scheduler_started = True
                self.scheduler_threads[task_name] = threading.Thread(target=self._scheduler, args=(task_name,),
                                                                     daemon=True)
                self.scheduler_threads[task_name].start()

                # Start the event loop thread
                threading.Thread(target=self._run_event_loop, args=(task_name,), daemon=True).start()

    # Stop the scheduler
    def _stop_scheduler(self, task_name: str, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        :param task_name: Task name.
        :param force_cleanup: Force the end of a running task
        Stop the scheduler and event loop, and forcibly kill all tasks if force_cleanup is True.
        :param system_operations: System execution metrics
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not self.task_queues[task_name].empty() or not len(self.running_tasks) == 0:
                if system_operations:
                    logger.warning(f"Io asyncio task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")

            with self.condition:
                self.scheduler_started = False
                self.scheduler_stop_event.set()
                self.condition.notify_all()

            if force_cleanup:
                # Forcibly cancel all running tasks
                self._cancel_all_running_tasks(task_name)
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear the task queue
            self._clear_task_queue(task_name)

            # Stop the event loop
            self._stop_event_loop(task_name)

            # Wait for the scheduler thread to finish
            self._join_scheduler_thread(task_name)

            # Clean up all task return results
            with self.condition:
                self.task_results.clear()

            # Reset parameters for scheduler restart
            if task_name in self.event_loops:
                del self.event_loops[task_name]
            if task_name in self.scheduler_threads:
                del self.scheduler_threads[task_name]
            if task_name in self.task_queues:
                del self.task_queues[task_name]

            logger.info(
                f"Scheduler and event loop for task {task_name} have stopped, all resources have been released and parameters reset")

    def stop_all_schedulers(self, force_cleanup: bool, system_operations: bool = False) -> None:
        """
        Stop all schedulers and event loops, and forcibly kill all tasks if force_cleanup is True.

        :param force_cleanup: Force the end of all running tasks.
        :param system_operations: System execution metrics.
        """
        with self.scheduler_lock:
            # Check if all tasks are completed
            if not all(q.empty() for q in self.task_queues.values()) or len(self.running_tasks) != 0:
                if system_operations:
                    logger.warning(f"Io asyncio task | detected running tasks | stopping operation terminated")
                    return None

            logger.warning("Exit cleanup")

            with self.condition:
                self.scheduler_started = False
                self.scheduler_stop_event.set()
                self.condition.notify_all()

            if force_cleanup:
                # Forcibly cancel all running tasks
                for task_name in list(self.running_tasks.keys()):  # Create a copy using list()
                    self._cancel_all_running_tasks(task_name)
                self.scheduler_stop_event.set()
            else:
                self.scheduler_stop_event.set()

            # Clear all task queues
            for task_name in list(self.task_queues.keys()):
                self._clear_task_queue(task_name)

            # Stop all event loops
            for task_name in list(self.event_loops.keys()):
                self._stop_event_loop(task_name)

            # Wait for all scheduler threads to finish
            for task_name in list(self.scheduler_threads.keys()):
                self._join_scheduler_thread(task_name)

            # Clean up all task return results
            with self.condition:
                self.task_results.clear()

            # Reset parameters for scheduler restart
            self.event_loops.clear()
            self.scheduler_threads.clear()
            self.task_queues.clear()

            logger.info(
                f"All schedulers and event loops have stopped, all resources have been released and parameters reset")

    # Task scheduler
    def _scheduler(self, task_name: str) -> None:
        asyncio.set_event_loop(self.event_loops[task_name])

        while not self.scheduler_stop_event.is_set():
            with self.condition:
                # Wait for the task queue to be not empty and the number of tasks in the current event loop is less than 3
                while (self.task_queues[task_name].empty() or self.task_counters[
                    task_name] >= config["maximum_event_loop_tasks"]) and not self.scheduler_stop_event.is_set():
                    self.condition.wait()

                if self.scheduler_stop_event.is_set():
                    break

                if self.task_queues[task_name].qsize() == 0:
                    continue

                task = self.task_queues[task_name].get()

            timeout_processing, task_name, task_id, func, args, kwargs = task

            future = asyncio.run_coroutine_threadsafe(self._execute_task(task), self.event_loops[task_name])

            with self.condition:
                self.running_tasks[task_id] = [future, task_name]
                self.task_counters[task_name] += 1  # Add task counters

    # A function that executes a task
    @memory_release_decorator
    async def _execute_task(self, task: Tuple[bool, str, str, Callable, Tuple, Dict]) -> Any:
        """
        Execute an asynchronous task.
        :param task: Tuple, including timeout processing flag, task name, task ID, task function, positional arguments, and keyword arguments.
        """
        # Unpack task tuple into local variables
        timeout_processing, task_name, task_id, func, args, kwargs = task

        try:
            if task_id in self.banned_task_ids:
                logger.warning(f"Io asyncio task | {task_id} | is banned and will be deleted")
                return

            # Modify the task status
            with self.condition:
                self.task_details[task_id]["start_time"] = time.time()
                self.task_details[task_id]["status"] = "running"

            logger.info(f"Start running io asyncio task | {task_id} | ")

            # If the task needs timeout processing, set the timeout time
            if timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"] + 5, swallow_exc=False):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=config["watch_dog_time"]
                    )
            else:
                result = await func(*args, **kwargs)

            # Store task return results, keep up to 2 results
            with self.condition:
                if task_id not in self.task_results:
                    self.task_results[task_id] = []
                self.task_results[task_id].append(result)
                if len(self.task_results[task_id]) > 2:
                    self.task_results[task_id].pop(0)  # Remove the oldest result

            # Update task status to "completed"
            with self.condition:
                self.task_details[task_id]["status"] = "completed"

        except asyncio.TimeoutError:
            logger.warning(f"Io asyncio task | {task_id} | timed out, forced termination")
            with self.condition:
                self.task_details[task_id]["status"] = "timeout"
                self.task_details[task_id]["end_time"] = 'NaN'
        except TimeoutException:
            logger.warning(f"Io asyncio task | {task_id} | timed out, forced termination")
            with self.condition:
                self.task_details[task_id]["status"] = "timeout"
                self.task_details[task_id]["end_time"] = 'NaN'
        except asyncio.CancelledError:
            logger.warning(f"Io asyncio task | {task_id} | was cancelled")
            with self.condition:
                self.task_details[task_id]["status"] = "cancelled"
        except Exception as e:
            logger.error(f"Io asyncio task | {task_id} | execution failed: {e}")
            with self.condition:
                self.task_details[task_id]["status"] = "failed"
                self._log_error(task_id, e)
        finally:
            # Opt-out will result in the deletion of the information and the following processing will not be possible
            with self.condition:
                if self.task_details.get(task_id, None) is None:
                    return None

                if not self.task_details[task_id].get("end_time") == "NaN":
                    self.task_details[task_id]["end_time"] = time.time()

                # Remove the task from running tasks dictionary
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                # Reduce task counters
                self.task_counters[task_name] -= 1

                # Check if all tasks are completed
                if self.task_queues[task_name].empty() and len(self.running_tasks) == 0:
                    self._reset_idle_timer(task_name)

                # Notify the scheduler to continue scheduling new tasks
                self.condition.notify()

                # Check the number of task information
                self._check_and_log_task_details()

    # Log error information during task execution
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
        with self.condition:
            self.error_logs.append(error_info)
            # If error logs exceed 10, remove the earliest one
            if len(self.error_logs) > 10:
                self.error_logs.pop(0)

    # The task scheduler closes the countdown
    def _reset_idle_timer(self, task_name: str) -> None:
        """
        Reset the idle timer for a specific task name.

        :param task_name: Task name.
        """
        with self.idle_timer_lock:
            if task_name in self.idle_timers and self.idle_timers[task_name] is not None:
                self.idle_timers[task_name].cancel()
            self.idle_timers[task_name] = threading.Timer(self.idle_timeout, self._stop_scheduler,
                                                          args=(task_name, False, True,))
            self.idle_timers[task_name].start()

    def _cancel_idle_timer(self, task_name: str) -> None:
        """
        Cancel the idle timer for a specific task name.

        :param task_name: Task name.
        """
        with self.idle_timer_lock:
            if task_name in self.idle_timers and self.idle_timers[task_name] is not None:
                self.idle_timers[task_name].cancel()
                self.idle_timers[task_name] = None

    def _clear_task_queue(self, task_name: str) -> None:
        """
        Clear the task queue for a specific task name.

        :param task_name: Task name.
        """
        while not self.task_queues[task_name].empty():
            self.task_queues[task_name].get()

    def _join_scheduler_thread(self, task_name: str) -> None:
        """
        Wait for the scheduler thread to finish for a specific task name.

        :param task_name: Task name.
        """
        if task_name in self.scheduler_threads and self.scheduler_threads[task_name].is_alive():
            self.scheduler_threads[task_name].join()

    def get_queue_info(self) -> Dict:
        """
        Get detailed information about the task queue.

        Returns:
            Dict: Dictionary containing queue size, number of running tasks, number of failed tasks, task details, and error logs.
        """
        with self.condition:
            queue_info = {
                "queue_size": sum(q.qsize() for q in self.task_queues.values()),
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

        :param task_id: Task ID.
        """
        with self.condition:
            if task_id in self.running_tasks:
                future = self.running_tasks[task_id][0]
                future.cancel()
                logger.warning(f"Io asyncio task | {task_id} | has been forcibly cancelled")
            else:
                logger.warning(f"Io asyncio task | {task_id} | does not exist or is already completed")

    def cancel_all_queued_tasks_by_name(self, task_name: str) -> None:
        """
        Cancel all queued tasks with the same name.

        :param task_name: Task name.
        """
        with self.condition:
            if task_name in self.task_queues:
                temp_queue = queue.Queue()
                while not self.task_queues[task_name].empty():
                    task = self.task_queues[task_name].get()
                    if task[1] == task_name:  # Use function name to match task name
                        logger.warning(
                            f"Io asyncio task | {task_name} | is waiting to be executed in the queue, has been deleted")
                    else:
                        temp_queue.put(task)

                # Put uncancelled tasks back into the queue
                while not temp_queue.empty():
                    self.task_queues[task_name].put(temp_queue.get())

    def ban_task_name(self, task_name: str) -> None:
        """
        Ban a task name from execution, delete tasks directly if detected and print information.

        :param task_name: Task name.
        """
        with self.condition:
            self.banned_task_ids.append(task_name)
            logger.warning(f"Io asyncio task | {task_name} | has been banned from execution")

            # Cancel all queued tasks with the banned task name
            self.cancel_all_queued_tasks_by_name(task_name)

    def allow_task_name(self, task_name: str) -> None:
        """
        Allow a banned task name to be executed again.

        :param task_name: Task name.
        """
        with self.condition:
            if task_name in self.banned_task_ids:
                self.banned_task_ids.remove(task_name)
                logger.info(f"Io asyncio task | {task_name} | is allowed for execution")
            else:
                logger.warning(f"Io asyncio task | {task_name} | is not banned, no action taken")

    # Obtain the information returned by the corresponding task
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task. If there is a result, return and delete the oldest result; if no result, return None.

        :param task_id: Task ID.
        :return: Task return result, if the task is not completed or does not exist, return None.
        """
        if task_id in self.task_results and self.task_results[task_id]:
            result = self.task_results[task_id].pop(0)  # Return and delete the oldest result
            with self.condition:
                if not self.task_results[task_id]:
                    del self.task_results[task_id]
            return result
        logger.warning(f"Io asyncio task | {task_id} | does not exist or has been completed and removed")
        return None

    def _run_event_loop(self, task_name: str) -> None:
        """
        Run the event loop for a specific task name.

        :param task_name: Task name.
        """
        asyncio.set_event_loop(self.event_loops[task_name])
        self.event_loops[task_name].run_forever()

    def _cancel_all_running_tasks(self, task_name: str) -> None:
        """
        Forcibly cancel all running tasks for a specific task name.

        :param task_name: Task name.
        """
        with self.condition:
            for task_id in list(self.running_tasks.keys()):  # Create a copy using list()
                if self.running_tasks[task_id][1] == task_name:
                    future = self.running_tasks[task_id][0]
                    if not future.done():  # Check if the task is completed
                        future.cancel()
                        logger.warning(f"Io asyncio task | {task_id} | has been forcibly cancelled")
                        # Update task status to "cancelled"
                        if task_id in self.task_details:
                            self.task_details[task_id]["status"] = "cancelled"
                            self.task_details[task_id]["end_time"] = time.time()
                        if task_id in self.task_results:
                            del self.task_results[task_id]

    def _stop_event_loop(self, task_name: str) -> None:
        """
        Stop the event loop for a specific task name.

        :param task_name: Task name.
        """
        if task_name in self.event_loops and self.event_loops[
            task_name].is_running():  # Ensure the event loop is running
            try:
                self.event_loops[task_name].call_soon_threadsafe(self.event_loops[task_name].stop)
                # Wait for the event loop thread to finish
                if task_name in self.scheduler_threads and self.scheduler_threads[task_name].is_alive():
                    self.scheduler_threads[task_name].join(timeout=1)  # Wait up to 1 second
                # Clean up all tasks and resources
                self._cancel_all_running_tasks(task_name)
                self._clear_task_queue(task_name)
                with self.condition:
                    self.task_details.clear()
                    self.task_results.clear()
            except Exception as e:
                logger.error(f"Io asyncio task | stopping event loop | error occurred: {e}")

    def _check_and_log_task_details(self) -> None:
        """
        Check if the number of task details exceeds the configured limit and remove those with specific statuses.
        """
        with self.condition:
            task_details_copy = self.task_details.copy()
            if len(task_details_copy) > config["maximum_task_info_storage"]:
                logger.warning(f"More than {config['maximum_task_info_storage']} task details detected. "
                               f"Cleaning up old task details.")

                # Filter out tasks with status 'failed', 'completed', or 'timeout'
                new_task_details = {task_id: details for task_id, details in task_details_copy.items()
                                    if details.get("status") in ["pending", "running"]}

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
        else:
            logger.warning(f"Io asyncio task | {task_id} | does not exist or has been completed and removed.")
            return None


# Instantiate object
io_async_task = IoAsyncTask()
