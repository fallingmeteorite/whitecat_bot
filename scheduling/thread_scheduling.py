from typing import Callable, Optional, Tuple

from .asyn_task_assignment import asyntask
from .line_task_assignment import linetask


def add_task(timeout_processing: bool, task_id: str, func: Callable, asynchronous: bool, *args, **kwargs) -> None:
    """
    向队列中添加任务，根据任务类型选择异步任务或线性任务。

    Args:
        timeout_processing: 是否启用超时处理。
        task_id: 任务 ID。
        func: 任务函数。
        asynchronous: 是否异步执行任务。
        args: 任务函数的位置参数。
        kwargs: 任务函数的关键字参数。
    """
    if asynchronous:
        # 运行异步任务
        asyntask.add_task(timeout_processing, task_id, func, *args, **kwargs)
    else:
        # 运行线性任务
        linetask.add_task(timeout_processing, task_id, func, *args, **kwargs)