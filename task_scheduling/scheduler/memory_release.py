# -*- coding: utf-8 -*-
import functools
import gc
from typing import Callable, Any


# Define memory release decorator
def memory_release_decorator(func: Callable) -> Callable:
    """
    Memory release decorator, used to clean up unreferenced objects after function execution.
    Supports handling circular references and invoking the garbage collector.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Execute the function
        result = func(*args, **kwargs)

        # Invoke Python's garbage collector
        gc.collect()

        return result

    return wrapper
