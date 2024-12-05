import datetime
import time

from common.log import logger
from core.wsbot import ws_manager
from core.backend import app
from scheduling.line_task_assignment import linetask
from scheduling.asyn_task_assignment import asyntask
from common.message_process import messageprocess

def main():
    start_time = datetime.datetime.now()
    """
    主函数用于同时运行WebSocket服务器和FastAPI应用。
    它通过多线程来实现两者的同时运行，并在接收到键盘中断时安全地停止这两个服务。
    """

    # 创建并运行WebSocket服务器线程
    ws_thread = ws_manager.create_job()
    ws_thread.start()

    # 创建并运行FastAPI应用线程
    fastapi_thread = app.create_job()
    fastapi_thread.start()


    # 等待键盘中断
    try:
        while True:
            time.sleep(1)
            pass  # 主线程等待，让其他守护线程运行
    except KeyboardInterrupt:
        end_time = datetime.datetime.now()
        time_difference = end_time - start_time
        logger.info(f"本次程序运行了{time_difference},正在停止所有进程...")
        ws_manager.alive = False

        # TODO 这里应该检查是否所有任务都已完成（如图像生成等）
        messageprocess.stop()# 停止消息接收
        linetask.stop_scheduler()# 停止调度线程
        asyntask.stop_scheduler()# 停止调度线程
        ws_thread.join(timeout=2)  # 等待WebSocket服务器线程结束，超时5秒
        fastapi_thread.join(timeout=2)  # 等待FastAPI应用线程结束，超时5秒
        logger.info("已停止")
        return


if __name__ == "__main__":
    main()
