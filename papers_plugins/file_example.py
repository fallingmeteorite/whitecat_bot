import json
import time

import websockets

from common.config import config


async def file_set(websocket, uid, nickname, gid, file_url):
    async with websockets.connect(f"{str(config['websocket_uri'])}:{str(config['websocket_port'])}") as websocket:
        msg = {
            "action": "get_group_file_url",
            "params": {
                'group_id': gid,
                "file_id": file_url,
            }}
        await websocket.send(json.dumps(msg))
        while True:
            data = json.loads(await websocket.recv())
            time.sleep(1.0)
            if data.get('status', None) == 'ok' and data['data'].get('url', None) is not None:
                file_url = data['data']['url'] + "pretags.json"


def register(file_manager):
    """
    注册到文件管理器。

    :param file_manager: 文件管理器实例。
    """
    file_manager.register_plugin(
        name="",
        asynchronous=True,  # 文件加载插件必须用异步,因为涉及到获取文件等操作
        timeout_processing=True,
        handler=lambda websocket, uid, nickname, gid, fileid: file_set(websocket, uid, nickname, gid,
                                                                       fileid),
    )
