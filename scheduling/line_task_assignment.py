import atexit
import gc
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import partial

from common.config import config
from common.log import logger


class LineTask:
    def __init__(self):
        # 定义一个队列来存储任务
        self.task_queue = queue.Queue()

        # 定义一个字典来存储正在执行的任务
        self.running_tasks = {}

        # 定义一个字典来存储任务的详细信息
        self.task_details = {}

        # 定义一个锁来保护对 running_tasks 和 task_details 的访问
        self.lock = threading.Lock()

        # 定义一个条件变量来控制调度线程的运行状态
        self.condition = threading.Condition()

        # 定义一个标志来表示调度线程是否已经启动
        self.scheduler_started = False

        # 定义任务超时时间（秒）
        self.TASK_TIMEOUT = config["watch_dog_time"]

        # 定义一个标志来表示调度线程是否应该停止
        self.scheduler_stop_event = threading.Event()

    def execute_task(self, task):
        """执行任务的函数"""
        id, func, args, kwargs = task
        logger.debug(f"开始运行线性任务,线性任务名称 {id}\n")
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"线性任务 {id} 执行失败: {e}")

    def scheduler(self):
        """调度函数"""
        # 设置最大并行任务,超过时排队等待
        with ThreadPoolExecutor(max_workers=4) as executor:
            while not self.scheduler_stop_event.is_set():
                with self.condition:
                    while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                        self.condition.wait()

                    if self.scheduler_stop_event.is_set():
                        break

                    if self.task_queue.qsize() == 0:
                        break

                    task = self.task_queue.get()

                    id, func, args, kwargs = task

                    with self.lock:
                        if id in self.running_tasks:
                            # 如果 id 已经在执行中，将任务重新放回队列
                            self.task_queue.put(task)
                        else:
                            # 否则，将任务提交给线程池执行
                            self.running_tasks[id] = True
                            self.task_details[id] = {
                                "start_time": time.time(),
                                "status": "running"
                            }
                            future = executor.submit(self.execute_task, task)
                            future.add_done_callback(partial(self.task_done, id))
                            # 启动一个线程来监控任务的超时
                            threading.Thread(target=self.monitor_task_timeout, args=(id, future)).start()

    def monitor_task_timeout(self, id, future):
        """监控任务超时的函数"""
        try:
            future.result(timeout=self.TASK_TIMEOUT)
        except TimeoutError:
            logger.warning(f"线性队列任务|{id}|超时,强制结束")
            future.cancel()
            with self.lock:
                if id in self.running_tasks:
                    del self.running_tasks[id]
                    self.task_details[id]["status"] = "timeout"

    def task_done(self, id, future):
        """任务完成后的回调函数"""
        logger.debug(f"主动回收内存中信息：{gc.collect()}")
        with self.lock:
            if id in self.running_tasks:
                del self.running_tasks[id]
                self.task_details[id]["status"] = "completed"
                self.task_details[id]["end_time"] = time.time()

    def add_task(self, id, func, *args, **kwargs):
        """向队列中添加任务"""
        if int(self.task_queue.qsize()) <= int(config["maximum_queue"]):
            self.task_queue.put((id, func, args, kwargs))

            # 如果调度线程还没有启动，启动它
            if not self.scheduler_started:
                self.start_scheduler()

            # 通知调度线程有新任务
            with self.condition:
                self.condition.notify()

    def start_scheduler(self):
        self.scheduler_started = True
        scheduler_thread = threading.Thread(target=self.scheduler)
        scheduler_thread.start()

    def stop_scheduler(self):
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

    def get_queue_info(self):
        """获取队列信息"""
        with self.lock:
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": len(self.running_tasks),
                "task_details": self.task_details.copy()
            }
        return queue_info


# 注册退出处理函数
linetask = LineTask()
atexit.register(linetask.stop_scheduler)
