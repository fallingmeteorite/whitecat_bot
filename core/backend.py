import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from utils.Job import Job
from common.log import logger

class Backend(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run_fastapi_app(self, host="localhost", port=8000):
        uvicorn.run(self, host=host, port=port, log_level="info")

    def create_job(self):
        fastapi_thread = Job(target=self.run_fastapi_app)
        fastapi_thread.daemon = True  # 设置线程为守护线程，以便在主程序停止时自动关闭
        return fastapi_thread


# 实例化类
app = Backend()

# 设置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/file/{path}/{file_id}")
def get_file(path: str, file_id: str):
    logger.debug(path,file_id)
    return FileResponse(f'./static/{path}/{file_id}')