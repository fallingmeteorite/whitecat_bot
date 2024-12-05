import json


async def main(websocket, uid, nickname, gid, file_url, ):
    msg = {
        "action": "get_group_file_url",
        "params": {
            'group_id': gid,
            "file_id": file_url,
        }}
    await websocket.send(json.dumps(msg))
    data = json.loads(await websocket.recv())


def register(file_manager):
    """
    注册到文件管理器。

    :param file_manager: 文件管理器实例。
    """
    file_manager.register_plugin(
        name="",
        asynchronous=True, #文件加载插件必须用异步,因为涉及到获取文件等操作
        handler=lambda websocket, uid, nickname, gid, fileid: main(websocket, uid, nickname, gid,
                                                                       fileid),
    )
