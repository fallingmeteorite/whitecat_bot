import asyncio
import atexit
import gc
import queue
import threading
import time

from common.config import config
from common.log import logger


class AsynTask:
    def __init__(self):
        self.loop = None

        # 定义一个队列来存储任务
        self.task_queue = queue.Queue()

        # 定义一个条件变量来控制调度线程的运行状态
        self.condition = threading.Condition()

        # 定义一个标志来表示调度线程是否已经启动
        self.scheduler_started = False

        # 定义任务超时时间（秒）
        self.TASK_TIMEOUT = config["watch_dog_time"]

        # 定义一个标志来表示调度线程是否应该停止
        self.scheduler_stop_event = threading.Event()

        # 定义一个字典来存储任务的详细信息
        self.task_details = {}

    async def execute_task(self, task):
        """执行任务的函数"""
        id, func, args, kwargs = task
        logger.debug(f"开始运行异步任务,异步任务名称 {id}")
        try:
            self.task_details[id] = {
                "start_time": time.monotonic(),
                "status": "running",
                "continue_timing": True  # 初始状态为继续计时
            }

            # 如果执行任务为定时器，不检测超时
            if id == "timer":
                await asyncio.wait_for(func(*args, **kwargs), timeout=None)
            else:
                await asyncio.wait_for(func(*args, **kwargs), timeout=self.TASK_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(f"队列任务|{id}|超时,强制结束")
            self.task_details[id]["status"] = "timeout"
        except Exception as e:
            logger.error(f"异步任务 {id} 执行失败: {e}")
            self.task_details[id]["status"] = "failed"
        finally:
            self.task_details[id]["end_time"] = time.monotonic()
            # 如果任务状态为 "running"，则将其设置为 "completed"
            if self.task_details[id]["status"] == "running":
                self.task_details[id]["status"] = "completed"
            logger.debug(f"主动回收内存中信息：{gc.collect()}")

    def scheduler(self):
        """调度函数"""
        asyncio.set_event_loop(self.loop)
        while not self.scheduler_stop_event.is_set():
            with self.condition:
                while self.task_queue.empty() and not self.scheduler_stop_event.is_set():
                    self.condition.wait()

                if self.scheduler_stop_event.is_set():
                    break

                if self.task_queue.qsize() == 0:
                    break

                task = self.task_queue.get()

                # 直接将任务提交给事件循环执行
                asyncio.run_coroutine_threadsafe(self.execute_task(task), self.loop)

    def add_task(self, id, func, *args, **kwargs):
        """向队列中添加任务"""
        if int(self.task_queue.qsize()) <= int(config["maximum_queue"]):
            self.task_queue.put((id, func, args, kwargs))

            # 如果调度线程还没有启动，启动它
            if not self.scheduler_started:
                self.loop = asyncio.new_event_loop()
                self.start_scheduler()

            # 通知调度线程有新任务
            with self.condition:
                self.condition.notify()

    def start_scheduler(self):
        self.scheduler_started = True
        scheduler_thread = threading.Thread(target=self.scheduler)
        scheduler_thread.start()

        # 启动事件循环线程
        event_loop_thread = threading.Thread(target=self.run_event_loop, args=())
        event_loop_thread.start()

    def run_event_loop(self):
        """运行事件循环的函数"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop_scheduler(self):
        self.scheduler_stop_event.set()
        with self.condition:
            self.condition.notify_all()

        # 停止事件循环,(防止时间循环还没开启就结束会引发报错)
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except:
            pass

    def get_queue_info(self):
        """获取队列信息"""
        with self.condition:
            running_tasks = [task_id for task_id, details in self.task_details.items() if details["status"] == "running"]
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": len(running_tasks),
                "task_details": self.task_details.copy()
            }
        return queue_info


# 注册退出处理函数
asyntask = AsynTask()
atexit.register(asyntask.stop_scheduler)
