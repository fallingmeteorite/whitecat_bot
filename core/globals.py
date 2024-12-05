from typing import Optional

from websockets import WebSocketClientProtocol


class PointerObj:
    def __init__(self, s, k: str):
        self.s = s
        self.k = k

    def __getattr__(self, item):
        if item in ['s', 'k']:
            return getattr(self, item)
        return getattr(getattr(self.s, self.k), item)

    def __setattr__(self, key, value):
        if key in ['s', 'k']:
            return super().__setattr__(key, value)
        return setattr(getattr(self.s, self.k), key, value)


class _Globals:
    def __init__(self):
        self._glob_ws: Optional[WebSocketClientProtocol] = None
        self._glob_ws_ptr = PointerObj(self, "_glob_ws")

    @property
    def ws(self):
        return self._glob_ws_ptr

    @ws.setter
    def ws(self, ws: WebSocketClientProtocol):
        self._glob_ws = ws


glob_instance = _Globals()
