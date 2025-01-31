import asyncio
import inspect
import json
import weakref
from typing import Optional, Dict, Any

from common import logger


def is_in_event_loop() -> bool:
    """
    检查当前是否在事件循环中运行。

    Returns:
        bool: 如果在事件循环中运行，返回 True；否则返回 False。
    """
    try:
        loop = asyncio.get_running_loop()
        return loop is not None and loop.is_running()
    except RuntimeError:
        return False


def send_message(websocket, uid: int, gid: Optional[int] = None, **kwargs: Any) -> None:
    """
    向客户端发送消息。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID（可选）。
        **kwargs: 其他消息参数。
    """
    # 获取调用者信息
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame.filename  # 获取文件名
    caller_line = caller_frame.lineno  # 获取行号
    caller_function = caller_frame.function  # 获取函数名
    logger.info(f"文件: {caller_file} 的第 {caller_line} 行的 {caller_function} 函数发送了消息")

    # 构建消息字典
    action = "send_private_msg" if gid is None else "send_group_msg"
    msg = {
        "action": action,
        "params": {
            "user_id": uid,
            "group_id": gid,
            **kwargs
        }
    }

    # 移除消息字典中值为 None 的键值对
    msg["params"] = {k: v for k, v in msg["params"].items() if v is not None}

    # 发送消息
    _send_json_message(websocket, msg)


def send_action(websocket, uid: int, gid: Optional[int] = None, action: str = None, **kwargs: Any) -> None:
    """
    向客户端发送指定操作的消息。

    Args:
        websocket: WebSocket 连接对象。
        uid: 用户 ID。
        gid: 群组 ID（可选）。
        action: 操作类型（如 napcat_api）。
        **kwargs: 其他消息参数。
    """
    # 获取调用者信息
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame.filename  # 获取文件名
    caller_line = caller_frame.lineno  # 获取行号
    caller_function = caller_frame.function  # 获取函数名
    logger.info(f"文件: {caller_file} 的第 {caller_line} 行的 {caller_function} 函数发送了消息")

    # 构建消息字典
    msg = {
        "action": action,
        "params": {
            "user_id": uid,
            "group_id": gid,
            **kwargs
        }
    }

    # 移除消息字典中值为 None 的键值对
    msg["params"] = {k: v for k, v in msg["params"].items() if v is not None}

    # 发送消息
    _send_json_message(websocket, msg)


def _send_json_message(websocket, msg: Dict[str, Any]) -> None:
    """
    将消息字典转换为 JSON 字符串并发送。

    Args:
        websocket: WebSocket 连接对象。
        msg: 消息字典。
    """
    # 使用弱引用存储 WebSocket 对象
    websocket_ref = weakref.ref(websocket)

    # 将消息字典转换为 JSON 字符串
    msg_json = json.dumps(msg, ensure_ascii=False)

    # 发送 JSON 格式的消息
    if is_in_event_loop():
        asyncio.create_task(websocket_ref().send(msg_json))
    else:
        asyncio.run(websocket_ref().send(msg_json))
