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
        # 定义一个标志来表示调度线程是否应该停止
        self.scheduler_stop_event = threading.Event()
        # 定义一个字典来存储任务的详细信息
        self.task_details = {}
        # 定义一个字典来存储任务的 asyncio.Task 对象
        self.running_tasks = {}
        # 定义一个列表来存储最近的报错信息，最多保留 10 条
        self.error_logs = []

    async def execute_task(self, task):
        """执行任务的函数"""
        timeout_processing, id, func, args, kwargs = task
        logger.debug(f"开始运行异步任务,异步任务名称 {id}")
        try:
            self.task_details[id] = {
                "start_time": time.monotonic(),
                "status": "running",
                "continue_timing": True  # 初始状态为继续计时
            }

            # 如果执行任务为定时器，不检测超时
            if timeout_processing:
                await asyncio.wait_for(func(*args, **kwargs), timeout=config["watch_dog_time"])
            else:
                await asyncio.wait_for(func(*args, **kwargs), timeout=None)
        except asyncio.TimeoutError:
            logger.warning(f"队列任务|{id}|超时,强制结束")
            self.task_details[id]["status"] = "timeout"
        except asyncio.CancelledError:
            logger.warning(f"队列任务|{id}|被强制取消")
            self.task_details[id]["status"] = "cancelled"
        except Exception as e:
            logger.error(f"异步任务 {id} 执行失败: {e}")
            self.task_details[id]["status"] = "failed"
            self.log_error(id, e)
        finally:
            self.task_details[id]["end_time"] = time.monotonic()
            # 如果任务状态为 "running"，则将其设置为 "completed"
            if self.task_details[id]["status"] == "running":
                self.task_details[id]["status"] = "completed"
            logger.debug(f"主动回收内存中信息：{gc.collect()}")
            # 从运行任务字典中移除该任务
            if id in self.running_tasks:
                del self.running_tasks[id]

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
                future = asyncio.run_coroutine_threadsafe(self.execute_task(task), self.loop)
                task_id = task[1]
                self.running_tasks[task_id] = future

    def add_task(self, timeout_processing, id, func, *args, **kwargs):
        """向队列中添加任务"""
        if int(self.task_queue.qsize()) <= int(config["maximum_queue"]):
            self.task_queue.put((timeout_processing, id, func, args, kwargs))

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
            running_tasks = [task_id for task_id, details in self.task_details.items() if
                             details["status"] == "running"]
            failed_tasks = [task_id for task_id, details in self.task_details.items() if
                            details["status"] == "failed"]
            queue_info = {
                "queue_size": self.task_queue.qsize(),
                "running_tasks_count": len(running_tasks),
                "failed_tasks_count": len(failed_tasks),
                "task_details": self.task_details.copy(),
                "error_logs": self.error_logs.copy()  # 返回最近的错误日志
            }
        return queue_info

    def force_stop_task(self, task_id):
        """通过任务ID强制关闭任务"""
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            future.cancel()
            logger.warning(f"任务 {task_id} 已被强制取消")
        else:
            logger.warning(f"任务 {task_id} 不存在或已完成")

    def log_error(self, id, exception):
        """记录错误信息"""
        error_info = {
            "task_id": id,
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
