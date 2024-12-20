import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from common.log import logger
from utils.Job import Job


class Backend(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 设置CORS中间件
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 挂载静态文件目录
        static_dir = "static"
        if os.path.exists(static_dir):
            self.mount("/static", StaticFiles(directory=static_dir), name="static")
        else:
            logger.warning(f"静态文件目录 '{static_dir}' 不存在，无法挂载。")

    def run_fastapi_app(self, host="localhost", port=8000):
        """
        启动 FastAPI 应用。
        """
        logger.info(f"启动 FastAPI 应用，监听地址: {host}:{port}")
        uvicorn.run(self, host=host, port=port, log_level="info")

    def create_job(self):
        fastapi_thread = Job(target=self.run_fastapi_app)
        fastapi_thread.daemon = True  # 设置线程为守护线程，以便在主程序停止时自动关闭
        return fastapi_thread


# 实例化 Backend 类
app = Backend()


@app.get("/file/{path}/{file_id}")
def get_file(path: str, file_id: str):
    """
    获取指定路径下的文件。

    参数:
    - path: 文件所在的目录路径。
    - file_id: 文件的唯一标识符。

    返回:
    - FileResponse: 返回请求的文件。
    """
    file_path = f"./static/{path}/{file_id}"
    logger.debug(f"请求文件: {file_path}")

    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"文件不存在: {file_path}")
        return {"error": "文件不存在"}
