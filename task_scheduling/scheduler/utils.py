import inspect
from typing import Callable


class AwaitDetector:
    def __init__(self):
        # Used to store the has_awaited status for different task_names
        self.task_status = {}

    def is_async_function(self, func: Callable) -> bool:
        """
        Determine if a function is an asynchronous function.

        :param func: The function to check

        :return: True if the function is asynchronous; otherwise, False.
        """
        return inspect.iscoroutinefunction(func)

    async def run_with_detection(self, task_name, func, *args, **kwargs):
        # Initialize the status for the current task_name
        self.task_status[task_name] = False

        # Check if the function is a coroutine function
        if not inspect.iscoroutinefunction(func):
            print(f"Task '{task_name}' is not a coroutine function and cannot perform await.")
            return await func(*args, **kwargs)

        # Check if the 'await' keyword is contained in the function body
        try:
            source = inspect.getsource(func)
            if "await" not in source:
                print(f"Task '{task_name}' does not contain 'await' in its source code.")
                return await func(*args, **kwargs)
        except (OSError, TypeError):
            # If the source code cannot be obtained (e.g., built-in functions), skip static checking
            pass

        # Define a wrapper to detect await
        async def wrapped_coroutine():
            self.task_status[task_name] = True
            return await func(*args, **kwargs)

        result = None
        try:
            # Run the wrapped coroutine
            result = await wrapped_coroutine()
            if not self.task_status[task_name]:
                print(f"Task '{task_name}' did not perform any await.")
            else:
                print(f"Task '{task_name}' performed await.")
        except Exception as e:
            print(f"Task '{task_name}' encountered an error: {e}")
        finally:
            # Reset the status for the current task_name
            self.task_status[task_name] = False
        if result is None:
            return None
        return result


# Create an instance of AwaitDetector
detector = AwaitDetector()
