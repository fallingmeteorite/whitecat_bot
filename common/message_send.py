import asyncio
import inspect
import json

from common.log import logger


def is_in_event_loop():
    try:
        loop = asyncio.get_running_loop()
        return loop is not None and loop.is_running()
    except RuntimeError:
        return False


def send_message(websocket, uid, gid, **kwargs):
    """
    向客户端发送消息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID（可选）。
    :param kwargs: 其他消息参数。
    """
    # 构建消息字典
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame[1]
    caller_line = caller_frame[2]
    caller_function = caller_frame[3]
    logger.info(f"检测到文件:{caller_file}的第{caller_line}行的{caller_function}函数发送了消息")

    msg = {
        "action": "send_private_msg" if gid is None else "send_group_msg",
        "params": {
            "user_id": uid,
            "group_id": gid,
            **kwargs
        }
    }

    # 移除消息字典中值为None的键值对
    msg["params"] = {k: v for k, v in msg["params"].items() if v is not None}

    # 将消息字典转换为JSON字符串
    msg_json = json.dumps(msg)
    # 发送JSON格式的消息
    # 判断是不是在asyncio.run()函数中执行
    if is_in_event_loop():
        asyncio.create_task(websocket.send(msg_json))
    else:
        asyncio.run(websocket.send(msg_json))


def send_action(websocket, uid, gid, action, **kwargs):
    """
    向客户端发送消息。

    :param websocket: WebSocket连接对象。
    :param uid: 用户ID。
    :param gid: 群组ID（可选）。
    :param action: napcat_api
    :param kwargs: 其他消息参数。
    """
    # 构建消息字典
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame[1]
    caller_line = caller_frame[2]
    caller_function = caller_frame[3]
    logger.info(f"检测到文件:{caller_file}的第{caller_line}行的{caller_function}函数发送了消息")

    msg = {
        "action": action,
        "params": {
            "user_id": uid,
            "group_id": gid,
            **kwargs
        }
    }

    # 移除消息字典中值为None的键值对
    msg["params"] = {k: v for k, v in msg["params"].items() if v is not None}

    # 将消息字典转换为JSON字符串
    msg_json = json.dumps(msg)

    # 发送JSON格式的消息
    # 判断是不是在asyncio.run()函数中执行
    if is_in_event_loop():
        asyncio.create_task(websocket.send(msg_json))
    else:
        asyncio.run(websocket.send(msg_json))
