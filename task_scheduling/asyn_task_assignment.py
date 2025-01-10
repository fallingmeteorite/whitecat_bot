import asyncio
import atexit
import gc
import queue
import threading
import time
from typing import Dict, List, Tuple, Callable, Optional
from weakref import WeakValueDictionary

from common.logging import logger
from config.config import config
from memory_management.memory_release import simple_memory_release_decorator


class AsynTask:
    """
    异步任务管理器类，负责管理异步任务的调度、执行和监控。
    """
    __slots__ = [
        'loop', 'task_queue', 'condition', 'scheduler_started', 'scheduler_stop_event',
        'task_details', 'running_tasks', 'error_logs'
    ]

    def __init__(self) -> None:
        """
        初始化异步任务管理器。
        """
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.task_queue = queue.Queue()  # 任务队列
        self.condition = threading.Condition()  # 条件变量，用于线程同步
        self.scheduler_started = False  # 调度线程是否已启动
        self.scheduler_stop_event = threading.Event()  # 调度线程停止事件
        self.task_details: Dict[str, Dict] = {}  # 任务详细信息
        self.running_tasks: WeakValueDictionary[str, asyncio.Task] = WeakValueDictionary()  # 使用弱引用减少内存占用
        self.error_logs: List[Dict] = []  # 错误日志，最多保留 10 条

    @simple_memory_release_decorator
    async def execute_task(self, task: Tuple[bool, str, Callable, Tuple, Dict]) -> None:
        """
        执行异步任务。

        :param task: 任务元组，包含超时处理标志、任务 ID、任务函数、位置参数和关键字参数。
        """
        timeout_processing, task_id, func, args, kwargs = task
        logger.debug(f"开始运行异步任务, 异步任务名称: {task_id}")
        try:
            self.task_details[task_id] = {
                "start_time": time.monotonic(),
                "status": "running"
            }

            # 如果任务需要超时处理，则设置超时时间
            if timeout_processing:
                await asyncio.wait_for(func(*args, **kwargs), timeout=config["watch_dog_time"])
            else:
                await func(*args, **kwargs)
        except asyncio.TimeoutError:
            logger.warning(f"队列任务 | {task_id} | 超时, 强制结束")
            self.task_details[task_id]["status"] = "timeout"
        except asyncio.CancelledError:
            logger.warning(f"队列任务 | {task_id} | 被强制取消")
            self.task_details[task_id]["status"] = "cancelled"
        except Exception as e:
            logger.error(f"异步任务 {task_id} 执行失败: {e}")
            self.task_details[task_id]["status"] = "failed"
            self.log_error(task_id, e)
        finally:
            logger.debug(f"主动回收内存为: {gc.collect()}")
            self.task_details[task_id]["end_time"] = time.monotonic()
            # 如果任务状态为 "running"，则将其设置为 "completed"
            if self.task_details[task_id]["status"] == "running":
                self.task_details[task_id]["status"] = "completed"
            # 从运行任务字典中移除该任务
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            # 显式删除任务中的临时变量
            del timeout_processing
            del task_id
            del func
            del args
            del kwargs

    def scheduler(self) -> None:
        """
        调度函数，从任务队列中取出任务并提交给事件循环执行。
        """
        asyncio.set_event_loop(self.loop)
        while not self.scheduler_stop_event.is_set():
            with self.condition:
                while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                    self.condition.wait()

                if self.scheduler_stop_event.is_set():
                    break

                if self.task_queue.qsize() == 0:
                    continue

                task = self.task_queue.get()
                task_id = task[1]

                # 如果任务已经在运行，跳过
                if task_id in self.running_tasks:
                    continue

                # 将任务提交给事件循环执行
                future = asyncio.run_coroutine_threadsafe(self.execute_task(task), self.loop)
                self.running_tasks[task_id] = future

    def add_task(self, timeout_processing: bool, task_id: str, func: Callable, *args, **kwargs) -> None:
        """
        向任务队列中添加任务。

        :param timeout_processing: 是否启用超时处理。
        :param task_id: 任务 ID。
        :param func: 任务函数。
        :param args: 任务函数的位置参数。
        :param kwargs: 任务函数的关键字参数。
        """
        if self.task_queue.qsize() <= config["maximum_queue_async"]:
            self.task_queue.put((timeout_processing, task_id, func, args, kwargs))

            # 如果调度线程还没有启动，启动它
            if not self.scheduler_started:
                self.loop = asyncio.new_event_loop()
                self.start_scheduler()

            # 通知调度线程有新任务
            with self.condition:
                self.condition.notify()

    def start_scheduler(self) -> None:
        """
        启动调度线程和事件循环线程。
        """
        self.scheduler_started = True
        scheduler_thread = threading.Thread(target=self.scheduler, daemon=True)
        scheduler_thread.start()

        # 启动事件循环线程
        event_loop_thread = threading.Thread(target=self.run_event_loop, daemon=True)
        event_loop_thread.start()

    def run_event_loop(self) -> None:
        """
        运行事件循环。
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop_scheduler(self) -> None:
        """
        停止调度线程和事件循环，并强制杀死所有任务。
        """
        logger.warning("退出清理")
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

        # 强制取消所有正在运行的任务
        for task_id, future in self.running_tasks.items():
            if not future.done():  # 检查任务是否已完成
                future.cancel()
                logger.warning(f"任务 {task_id} 已被强制取消")

        # 停止事件循环
        if self.loop and self.loop.is_running():  # 确保事件循环正在运行
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception as e:
                logger.error(f"停止事件循环时发生错误: {e}")

    def get_queue_info(self) -> Dict:
        """
        获取任务队列的详细信息。

        Returns:
            Dict: 包含队列大小、运行任务数量、失败任务数量、任务详细信息和错误日志的字典。
        """
        with self.condition:
            running_tasks = [task_id for task_id, details in self.task_details.items() if
                             details.get("status") == "running"]
            failed_tasks = [task_id for task_id, details in self.task_details.items() if
                            details.get("status") == "failed"]
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": len(running_tasks),
                "failed_tasks_count": len(failed_tasks),
                "task_details": self.task_details.copy(),
                "error_logs": self.error_logs.copy()  # 返回最近的错误日志
            }
        return queue_info

    def force_stop_task(self, task_id: str) -> None:
        """
        通过任务 ID 强制停止任务。

        :param task_id: 任务 ID。
        """
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            future.cancel()
            logger.warning(f"任务 {task_id} 已被强制取消")
        else:
            logger.warning(f"任务 {task_id} 不存在或已完成")

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
        with self.condition:
            self.error_logs.append(error_info)
            # 如果错误日志超过 10 条，移除最早的一条
            if len(self.error_logs) > 10:
                self.error_logs.pop(0)


# 注册退出处理函数
asyntask = AsynTask()
atexit.register(asyntask.stop_scheduler)
