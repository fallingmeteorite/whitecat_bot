""":module: watchdog.utils
:synopsis: Utility classes and functions.
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Classes
-------
.. autoclass:: BaseThread
   :members:
   :show-inheritance:
   :inherited-members:

"""

from __future__ import annotations

import threading

from .events import *


class UnsupportedLibcError(Exception):
    pass


class WatchdogShutdownError(Exception):
    """Semantic exception used to signal an external shutdown event."""


class BaseThread(threading.Thread):
    """Convenience class for creating stoppable threads."""

    def __init__(self) -> None:
        threading.Thread.__init__(self)
        if hasattr(self, "daemon"):
            self.daemon = True
        else:
            self.setDaemon(True)
        self._stopped_event = threading.Event()

    @property
    def stopped_event(self) -> threading.Event:
        return self._stopped_event

    def should_keep_running(self) -> bool:
        """Determines whether the thread should continue running."""
        return not self._stopped_event.is_set()

    def on_thread_stop(self) -> None:
        """Override this method instead of :meth:`stop()`.
        :meth:`stop()` calls this method.

        This method is called immediately after the thread is signaled to stop.
        """

    def stop(self) -> None:
        """Signals the thread to stop."""
        self._stopped_event.set()
        self.on_thread_stop()

    def on_thread_start(self) -> None:
        """Override this method instead of :meth:`start()`. :meth:`start()`
        calls this method.

        This method is called right before this thread is started and this
        object's run() method is invoked.
        """

    def start(self) -> None:
        self.on_thread_start()
        threading.Thread.start(self)
