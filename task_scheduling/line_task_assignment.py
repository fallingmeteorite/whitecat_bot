import gc
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, Dict, List, Tuple
from weakref import WeakValueDictionary

from common.logging import logger
from config.config import config
from memory_management.memory_release import simple_memory_release_decorator
from task_scheduling.task_destruction import manager
from task_scheduling.threadstop import ThreadingTimeout, TimeoutException


class LineTask:
    """
    线性任务管理器类，负责管理线性任务的调度、执行和监控。
    """
    __slots__ = [
        'task_queue', 'running_tasks', 'task_details', 'lock', 'condition',
        'scheduler_started', 'scheduler_stop_event', 'error_logs', 'scheduler_thread'
    ]

    def __init__(self) -> None:
        """
        初始化线性任务管理器。
        """
        self.task_queue = queue.Queue()  # 任务队列
        self.running_tasks: WeakValueDictionary[str, ThreadPoolExecutor] = WeakValueDictionary()  # 正在执行的任务
        self.task_details: Dict[str, Dict] = {}  # 任务详细信息
        self.lock = threading.Lock()  # 锁，用于保护对共享资源的访问
        self.condition = threading.Condition()  # 条件变量，用于线程同步
        self.scheduler_started = False  # 调度线程是否已启动
        self.scheduler_stop_event = threading.Event()  # 调度线程停止事件
        self.error_logs: List[Dict] = []  # 错误日志，最多保留 10 条
        self.scheduler_thread: threading.Thread  # 调度线程

    @simple_memory_release_decorator
    def execute_task(self, task: Tuple[bool, str, Callable, Tuple, Dict]) -> None:
        """
        执行线性任务。

        :param task: 任务元组，包含超时处理标志、任务 ID、任务函数、位置参数和关键字参数。
        """
        timeout_processing, task_id, func, args, kwargs = task
        logger.debug(f"开始运行线性任务, 线性任务名称: {task_id}")

        # 超时处理和任务执行
        try:
            if timeout_processing:
                with ThreadingTimeout(seconds=config["watch_dog_time"], swallow_exc=False) as task_control:
                    # 将停止函数方法放入字典中
                    manager.add(task_control, task_id)
                    func(*args, **kwargs)
                    # 将停止函数方法从字典中移除
                    manager.remove(task_id)
            else:
                with ThreadingTimeout(seconds=None, swallow_exc=True) as task_control:
                    # 将停止函数方法放入字典中
                    manager.add(task_control, task_id)
                    func(*args, **kwargs)
                    # 将停止函数方法从字典中移除
                    manager.remove(task_id)
        finally:
            # 显式删除不再使用的变量
            del timeout_processing, task_id, func, args, kwargs

    def scheduler(self) -> None:
        """
        调度函数，从任务队列中取出任务并提交给线程池执行。
        """
        with ThreadPoolExecutor(max_workers=int(config["line_task_max"])) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    # 如果没有任务就跳过
                    if self.task_queue.qsize() == 0:
                        continue

                    task = self.task_queue.get()

                _, task_id, _, _, _ = task

                with self.lock:
                    if task_id in self.running_tasks:
                        self.task_queue.put(task)
                        continue

                    self.running_tasks[task_id] = executor
                    self.task_details[task_id] = {
                        "start_time": time.time(),
                        "status": "running"
                    }
                # 提交任务
                future = executor.submit(self.execute_task, task)
                # 添加完成后执行函数
                future.add_done_callback(partial(self.task_done, task_id))

                # 启动一个线程来监控 future 的状态
                threading.Thread(target=self.monitor_future_status, args=(task_id, future)).start()

                # 将 future 对象与任务 ID 关联
                with self.lock:
                    self.running_tasks[task_id] = future

    def monitor_future_status(self, task_id: str, future: ThreadPoolExecutor) -> None:
        """
        监控 future 的状态，记录任务的执行情况。

        :param task_id: 任务 ID。
        :param future: 任务对应的 future 对象。
        """
        while not future.done():
            time.sleep(18)  # 每隔 18 秒检查一次
            # 监控 future 的状态
            if future.running():
                logger.debug(f"任务 {task_id} 正在运行")
            elif future.cancelled():
                logger.warning(f"任务 {task_id} 已被取消")

        # 任务完成后记录状态
        if future.done():
            if future.cancelled():
                logger.warning(f"任务 {task_id} 已被取消")
            elif future.exception():
                logger.error(f"任务 {task_id} 执行失败: {future.exception()}")
            else:
                logger.debug(f"任务 {task_id} 已完成")

    def task_done(self, task_id: str, future: ThreadPoolExecutor) -> None:
        """
        任务完成后的回调函数。

        :param task_id: 任务 ID。
        :param future: 任务对应的 future 对象。
        """
        try:
            future.result()  # 获取任务结果，如果有异常会在这里抛出
            self.update_task_status(task_id, "completed")
        except TimeoutException:
            logger.warning(f"线性队列任务 | {task_id} | 超时, 强制结束")
            self.update_task_status(task_id, "timeout")
        except Exception as e:
            logger.error(f"线性任务 {task_id} 执行失败: {e}")
            self.update_task_status(task_id, "failed")
            self.log_error(task_id, e)
        finally:
            logger.debug(f"主动回收内存为: {gc.collect()}")

    def update_task_status(self, task_id: str, status: str) -> None:
        """
        更新任务状态。

        :param task_id: 任务 ID。
        :param status: 任务状态。
        """
        with self.lock:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
                self.task_details[task_id]["status"] = status
                self.task_details[task_id]["end_time"] = time.time()

    def log_error(self, task_id: str, exception: Exception) -> None:
        """
        记录任务执行过程中的错误信息。

        :param task_id: 任务 ID。
        :param exception: 异常对象。
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

        :param timeout_processing: 是否启用超时处理。
        :param task_id: 任务 ID。
        :param func: 任务函数。
        :param args: 任务函数的位置参数。
        :param kwargs: 任务函数的关键字参数。
        """
        if self.task_queue.qsize() <= config["maximum_queue_line"]:
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
        self.scheduler_thread = threading.Thread(target=self.scheduler)
        self.scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """
        停止调度线程，并强制杀死所有任务。
        """
        logger.warning("退出清理")
        # 尝试关闭所有正在运行的任务
        manager.stop_all()
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

        # 强制取消所有正在运行的任务
        with self.lock:
            for task_id, future in self.running_tasks.items():
                # 取消还没有执行的任务
                future.cancel()
                logger.warning(f"任务 {task_id} 已被强制取消")
                self.update_task_status(task_id, "cancelled")

        # 清空任务队列
        while not self.task_queue.empty():
            self.task_queue.get()

        # 等待调度线程结束

        if self.scheduler_started:
            if self.scheduler_thread.is_alive():
                self.scheduler_thread.join()

        logger.info("调度线程已停止，所有资源已释放")

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
        通过任务 ID 强制停止任务，并手动触发超时。

        Args:
            task_id: 任务 ID。
        """
        with self.lock:
            if task_id in self.running_tasks:
                manager.stop(task_id)
                logger.warning(f"任务 {task_id} 已被强制取消")
                self.update_task_status(task_id, "cancelled")
            else:
                logger.warning(f"任务 {task_id} 不存在或已完成")


# 实例化对象
linetask = LineTask()
