import os
import signal
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from common.logging import logger


class Backend(FastAPI):
    """
    FastAPI 后端应用类，封装了应用初始化和信号处理逻辑。
    """

    def __init__(self, *args, **kwargs):
        """
        初始化后端应用，注册信号处理函数并配置中间件和静态文件目录。
        """
        # 注册信号处理函数
        signal.signal(signal.SIGINT, self.handle_signal)  # 处理 Ctrl+C
        signal.signal(signal.SIGTERM, self.handle_signal)  # 处理终止信号
        super().__init__(*args, **kwargs)

        # 配置 CORS 中间件
        self._configure_cors()
        # 挂载静态文件目录
        self._mount_static_files()

    def _configure_cors(self):
        """
        配置 CORS 中间件，允许跨域请求。
        """
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 允许所有来源
            allow_credentials=True,  # 允许携带凭证
            allow_methods=["*"],  # 允许所有 HTTP 方法
            allow_headers=["*"],  # 允许所有 HTTP 头
        )

    def _mount_static_files(self):
        """
        挂载静态文件目录，如果目录存在。
        """
        static_dir = "files_cache"
        if os.path.exists(static_dir):
            self.mount("/files_cache", StaticFiles(directory=static_dir), name="files_cache")
            logger.info(f"静态文件目录 '{static_dir}' 已挂载。")
        else:
            logger.warning(f"静态文件目录 '{static_dir}' 不存在，无法挂载。")

    def run_fastapi_app(self, host: str = "localhost", port: int = 8000):
        """
        启动 FastAPI 应用。

        Args:
            host: 监听的主机地址，默认为 "localhost"。
            port: 监听的端口号，默认为 8000。
        """
        logger.info(f"启动 FastAPI 应用，监听地址: {host}:{port}")
        uvicorn.run(self, host=host, port=port, log_level="info")

    def handle_signal(self, signum: int, frame):
        """
        处理信号（如 Ctrl+C 或终止信号），优雅地停止应用。

        Args:
            signum: 信号编号。
            frame: 当前的堆栈帧。
        """
        logger.info(f"接收到信号 {signum}，停止应用...")
        sys.exit(0)


def file_monitor():
    """
    文件监控进程，检查环境变量并在满足条件时停止 FastAPI 应用。
    """
    while True:
        try:
            if os.path.exists("./restart_fastapi.txt"):
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

    Args:
        path: 文件所在的目录路径。
        file_id: 文件的唯一标识符。

    Returns:
        FileResponse: 返回请求的文件。

    Raises:
        HTTPException: 如果文件不存在，返回 404 错误。
    """
    file_path = f"./cache_files/{path}/{file_id}"
    logger.debug(f"请求文件: {file_path}")

    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="文件不存在")


def main():
    """
    主函数，启动文件监控进程和 FastAPI 应用。
    """
    # 启动文件监控进程
    threading.Thread(target=file_monitor, daemon=True).start()
    # 启动 FastAPI 应用
    app.run_fastapi_app()



try:
    main()
except KeyboardInterrupt:
    logger.info("应用已手动停止。")
