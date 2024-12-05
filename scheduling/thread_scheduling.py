from .line_task_assignment import linetask
from .asyn_task_assignment import asyntask

def add_task(id, func, asynchronous, *args, **kwargs):
    """向队列中添加任务"""
    # 插件的参数,判断将执行的任务放在异步还是线程池
    if asynchronous:
        # 运行异步任务
        asyntask.add_task(id, func, *args, **kwargs)
    else:
        # 运行线性任务
        linetask.add_task(id, func, *args, **kwargs)