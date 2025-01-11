import json
import time
from typing import Dict, Optional, Any

import websockets

from common.logging import logger
from config.config import config


async def send_websocket_message(websocket: Any, message: Dict) -> Optional[Dict]:
    """
    发送 WebSocket 消息并接收响应。

    :param websocket: WebSocket 连接对象。
    :param message: 要发送的消息字典。
    :return: 接收到的响应数据，如果出错则返回 None。
    """
    try:
        await websocket.send(json.dumps(message))
        response = await websocket.recv()
        return json.loads(response)
    except Exception as e:
        logger.error(f"WebSocket 消息发送或接收时出错: {e}")
        return None


async def get_file_url(websocket: Any, gid: str, file_id: str) -> Optional[str]:
    """
    获取文件 URL。

    :param websocket: WebSocket 连接对象。
    :param gid: 群组 ID。
    :param file_id: 文件 ID。
    :return: 文件 URL，如果获取失败则返回 None。
    """
    message = {
        "action": "get_group_file_url",
        "params": {
            "group_id": gid,
            "file_id": file_id,
        }
    }

    while True:
        data = await send_websocket_message(websocket, message)
        if data and data.get("status") == "ok" and data["data"].get("url"):
            return data["data"]["url"] + "pretags.json"
        time.sleep(1.0)  # 等待一秒并重试


async def file_set(websocket: Any, uid: str, nickname: str, gid: str, file_id: str) -> None:
    """
    处理文件 URL 获取逻辑。

    :param websocket: WebSocket 连接对象。
    :param uid: 用户 ID。
    :param nickname: 用户昵称。
    :param gid: 群组 ID。
    :param file_id: 文件 ID。
    """
    websocket_uri = f"{config['websocket_uri']}:{config['websocket_port']}"
    try:
        async with websockets.connect(websocket_uri) as ws:
            file_url = await get_file_url(ws, gid, file_id)
            if file_url:
                logger.info(f"成功获取文件 URL: {file_url}")
            else:
                logger.warning("未能获取文件 URL")
    except Exception as e:
        logger.error(f"WebSocket 连接或文件 URL 获取时出错: {e}")


def register(file_manager) -> None:
    """
    注册到文件管理器。

    :param file_manager: 文件管理器实例。
    """
    file_manager.register_file(
        name="文件 URL 获取插件",
        asynchronous=True,  # 文件加载插件必须用异步，因为涉及到获取文件等操作
        timeout_processing=True,
        handler=file_set
    )
