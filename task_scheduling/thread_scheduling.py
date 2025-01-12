import atexit
import sys
from typing import Callable

from common.logging import logger
from .asyn_task_assignment import asyntask
from .line_task_assignment import linetask


def add_task(timeout_processing: bool, task_id: str, func: Callable, asynchronous: bool, *args, **kwargs) -> None:
    """
    向队列中添加任务，根据任务类型选择异步任务或线性任务。

    :param timeout_processing: 是否启用超时处理。
    :param task_id: 任务 ID。
    :param func: 任务函数。
    :param asynchronous: 是否异步执行任务。
    :param args: 任务函数的位置参数。
    :param kwargs: 任务函数的关键字参数。
    """
    if asynchronous:
        # 运行异步任务
        asyntask.add_task(timeout_processing, task_id, func, *args, **kwargs)
    else:
        # 运行线性任务
        linetask.add_task(timeout_processing, task_id, func, *args, **kwargs)

    # 显式删除不再使用的变量（可选）
    del timeout_processing
    del task_id
    del func
    del asynchronous


def stop_task():
    logger.info("正在停止调度器...")
    try:
        asyntask.stop_scheduler()
    except:
        pass
    try:
        linetask.stop_scheduler()
    except:
        pass


atexit.register(stop_task)
