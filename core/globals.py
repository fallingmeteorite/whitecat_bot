from typing import Optional

from websockets import WebSocketClientProtocol


class _Globals:
    def __init__(self):
        self._glob_ws: Optional[WebSocketClientProtocol] = None

    @property
    def ws(self) -> Optional[WebSocketClientProtocol]:
        """
        获取当前的 WebSocket 连接对象。

        返回:
        - Optional[WebSocketClientProtocol]: WebSocket 连接对象，如果未设置则为 None。
        """
        return self._glob_ws

    @ws.setter
    def ws(self, ws: WebSocketClientProtocol):
        """
        设置当前的 WebSocket 连接对象。

        参数:
        - ws (WebSocketClientProtocol): 要设置的 WebSocket 连接对象。
        """
        self._glob_ws = ws


# 全局实例
glob_instance = _Globals()
