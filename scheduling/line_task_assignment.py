import atexit
import gc
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import partial
from typing import Callable, Dict, List, Tuple

from common.config import config
from common.logging import logger


class LineTask:
    """
    线性任务管理器类，负责管理线性任务的调度、执行和监控。
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'task_details', 'lock', 'condition',
        'scheduler_started', 'scheduler_stop_event', 'error_logs'
    ]

    def __init__(self):
        """
        初始化线性任务管理器。
        """
        self.task_queue = queue.Queue()  # 任务队列
        self.running_tasks: Dict[str, ThreadPoolExecutor] = {}  # 正在执行的任务
        self.task_details: Dict[str, Dict] = {}  # 任务详细信息
        self.lock = threading.Lock()  # 锁，用于保护对共享资源的访问
        self.condition = threading.Condition()  # 条件变量，用于线程同步
        self.scheduler_started = False  # 调度线程是否已启动
        self.scheduler_stop_event = threading.Event()  # 调度线程停止事件
        self.error_logs: List[Dict] = []  # 错误日志，最多保留 10 条

    def execute_task(self, task: Tuple[bool, str, Callable, Tuple, Dict]) -> None:
        """
        执行线性任务。

        Args:
            task: 任务元组，包含超时处理标志、任务 ID、任务函数、位置参数和关键字参数。
        """
        _, task_id, func, args, kwargs = task
        logger.debug(f"开始运行线性任务, 线性任务名称: {task_id}")
        func(*args, **kwargs)

    def scheduler(self) -> None:
        """
        调度函数，从任务队列中取出任务并提交给线程池执行。
        """
        with ThreadPoolExecutor(max_workers=4) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        continue

                    task = self.task_queue.get()

                timeout_processing, task_id, _, _, _ = task

                with self.lock:
                    if task_id in self.running_tasks:
                        self.task_queue.put(task)
                        continue

                    self.running_tasks[task_id] = executor
                    self.task_details[task_id] = {
                        "start_time": time.time(),
                        "status": "running"
                    }

                future = executor.submit(self.execute_task, task)
                future.add_done_callback(partial(self.task_done, task_id))
                if timeout_processing:
                    # 启动一个线程来监控任务的超时
                    threading.Thread(target=self.monitor_task_timeout, args=(task_id, future)).start()

                # 将 future 对象与任务 ID 关联
                with self.lock:
                    self.running_tasks[task_id] = future

    def monitor_task_timeout(self, task_id: str, future: ThreadPoolExecutor) -> None:
        """
        监控任务超时。

        Args:
            task_id: 任务 ID。
            future: 任务对应的 future 对象。
        """
        try:
            future.result(timeout=config["watch_dog_time"])
        except TimeoutError:
            logger.warning(f"线性队列任务 | {task_id} | 超时, 强制结束")
            future.cancel()
            self.update_task_status(task_id, "timeout")
        finally:
            logger.debug(f"主动回收内存为:{gc.collect()}")

    def task_done(self, task_id: str, future: ThreadPoolExecutor) -> None:
        """
        任务完成后的回调函数。

        Args:
            task_id: 任务 ID。
            future: 任务对应的 future 对象。
        """
        try:
            future.result()  # 获取任务结果，如果有异常会在这里抛出
            self.update_task_status(task_id, "completed")
        except Exception as e:
            logger.error(f"线性任务 {task_id} 执行失败: {e}")
            self.update_task_status(task_id, "failed")
            self.log_error(task_id, e)
        finally:
            logger.debug(f"主动回收内存为:{gc.collect()}")

    def update_task_status(self, task_id: str, status: str) -> None:
        """
        更新任务状态。

        Args:
            task_id: 任务 ID。
            status: 任务状态。
        """
        with self.lock:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
                self.task_details[task_id]["status"] = status
                self.task_details[task_id]["end_time"] = time.time()

    def log_error(self, task_id: str, exception: Exception) -> None:
        """
        记录任务执行过程中的错误信息。

        Args:
            task_id: 任务 ID。
            exception: 异常对象。
        """
        error_info = {
            "task_id": task_id,
            "error_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "error_message": str(exception)
        }
        with self.lock:
            self.error_logs.append(error_info)
            # 如果错误日志超过 10 条，移除最早的一条
            if len(self.error_logs) > 10:
                self.error_logs.pop(0)

    def add_task(self, timeout_processing: bool, task_id: str, func: Callable, *args, **kwargs) -> None:
        """
        向任务队列中添加任务。

        Args:
            timeout_processing: 是否启用超时处理。
            task_id: 任务 ID。
            func: 任务函数。
            args: 任务函数的位置参数。
            kwargs: 任务函数的关键字参数。
        """
        if self.task_queue.qsize() <= config["maximum_queue"]:
            self.task_queue.put((timeout_processing, task_id, func, args, kwargs))

            if not self.scheduler_started:
                self.start_scheduler()

            with self.condition:
                self.condition.notify()

    def start_scheduler(self) -> None:
        """
        启动调度线程。
        """
        self.scheduler_started = True
        scheduler_thread = threading.Thread(target=self.scheduler)
        scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """
        停止调度线程，并强制杀死所有任务。
        """
        logger.warning("退出清理")
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

        # 强制取消所有正在运行的任务
        with self.lock:
            for task_id, future in self.running_tasks.items():
                future.cancel()
                logger.warning(f"任务 {task_id} 已被强制取消")
                self.update_task_status(task_id, "cancelled")

    def get_queue_info(self) -> Dict:
        """
        获取任务队列的详细信息。

        Returns:
            Dict: 包含队列大小、运行任务数量、任务详细信息和错误日志的字典。
        """
        with self.lock:
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": len(self.running_tasks),
                "task_details": self.task_details.copy(),
                "error_logs": self.error_logs.copy()  # 返回最近的错误日志
            }
        return queue_info

    def force_stop_task(self, task_id: str) -> None:
        """
        通过任务 ID 强制停止任务。

        Args:
            task_id: 任务 ID。
        """
        with self.lock:
            if task_id in self.running_tasks:
                future = self.running_tasks[task_id]
                future.cancel()
                logger.warning(f"任务 {task_id} 已被强制取消")
                self.update_task_status(task_id, "cancelled")
            else:
                logger.warning(f"任务 {task_id} 不存在或已完成")


# 注册退出处理函数
linetask = LineTask()
atexit.register(linetask.stop_scheduler)
