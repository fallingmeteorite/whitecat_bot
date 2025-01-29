import ctypes
import threading
from contextlib import contextmanager


class StopException(Exception):
    """Custom timeout exception"""
    pass


def async_raise(target_tid, exception):
    """Raise an asynchronous exception in the target thread"""
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), ctypes.py_object(exception))
    if ret == 0:
        raise ValueError("Invalid thread ID {}".format(target_tid))
    elif ret > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class SkipContext:
    """Context object for skipping the current line"""

    def __init__(self):
        self.target_tid = threading.current_thread().ident

    def skip(self):
        """Skip the current line"""
        async_raise(self.target_tid, StopException)


@contextmanager
def skip_on_demand():
    """Context manager that supports manual skipping of the current line"""
    skip_ctx = SkipContext()
    try:
        yield skip_ctx  # Provide skip_ctx to external code
    except StopException:
        return  # Exit directly, skipping all code within the with block
