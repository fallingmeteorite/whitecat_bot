import os
import signal
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from common.logging import logger


class Backend(FastAPI):
    def __init__(self, *args, **kwargs):
        # 注册信号处理函数
        signal.signal(signal.SIGINT, self.handle_signal)  # 处理 Ctrl+C
        signal.signal(signal.SIGTERM, self.handle_signal)  # 处理终止信号
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
        static_dir = "cache_files"
        if os.path.exists(static_dir):
            self.mount("/cache_files", StaticFiles(directory=static_dir), name="cache_files")
        else:
            logger.warning(f"静态文件目录 '{static_dir}' 不存在，无法挂载。")

    def run_fastapi_app(self, host="localhost", port=8000):
        """
        启动 FastAPI 应用。
        """
        logger.info(f"启动 FastAPI 应用，监听地址: {host}:{port}")
        uvicorn.run(self, host=host, port=port, log_level="info")

    def handle_signal(self, signum, frame):
        """
        处理信号（如 Ctrl+C 或终止信号）。
        """
        logger.info(f"接收到信号 {signum}，停止应用...")
        sys.exit(0)


def file_monitor():
    """
    文件监控进程，检查文件内容并在满足条件时停止 FastAPI 应用。
    """
    while True:
        try:
            if os.path.exists("./restart_fastapi.txt"):
                with open("./restart_fastapi.txt", "r") as file:
                    if file.read().strip() == "restart":
                        logger.info("监控到停止条件，准备停止 FastAPI 应用...")
                        os.kill(os.getpid(), signal.SIGTERM)
                        os.remove("restart_fastapi.txt")
                        break
            time.sleep(2)  # 每隔2秒检查一次文件
        except KeyboardInterrupt:
            sys.exit(0)


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
    file_path = f"./cache_files/{path}/{file_id}"
    logger.debug(f"请求文件: {file_path}")

    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"文件不存在: {file_path}")
        return {"error": "文件不存在"}


def main():
    # 启动文件监控进程
    threading.Thread(target=file_monitor, daemon=True).start()
    # 启动 FastAPI 应用
    app.run_fastapi_app()


try:
    main()
except KeyboardInterrupt:
    pass
