from .line_task_assignment import linetask
from .asyn_task_assignment import asyntask

def add_task(id, func, asynchronous, *args, **kwargs):
    """向队列中添加任务"""
    if asynchronous:
        asyntask.add_task(id, func, *args, **kwargs)
    else:
        linetask.add_task(id, func, *args, **kwargs)