import datetime
import os
import time
from typing import Optional

from common.config import config
from common.logging import logger
from utils.thread_creation import ThreadController
from  memory_cleanup.memory_release import simple_memory_release_decorator

class Application:
    """
    应用程序类，负责管理 WebSocket 服务器和 FastAPI 应用的启动、停止和重启。
    """

    def __init__(self):
        """
        初始化应用程序。
        """
        self.ws_thread: Optional[ThreadController] = None
        self.start_time: Optional[datetime.datetime] = None
        self.restart_value = True

    def check_py_files(self) -> bool:
        """
        Returns:
            bool: 如果存在文件返回 True，否则返回 False。
        """
        # 检查路径是否存在
        if len(os.listdir(config["adapter_dir"])) - 2 == 0:
            return False
        return True

    def run(self) -> None:
        """
        主函数用于同时运行 WebSocket 服务器和 FastAPI 应用。
        它通过多线程来实现两者的同时运行，并在接收到键盘中断时安全地停止这两个服务。
        """
        if not self.check_py_files():
            raise Exception("文件夹内没有可用适配器,进程退出")

        self.start_time = datetime.datetime.now()

        # 创建并运行 WebSocket 服务器线程
        self.ws_thread = ThreadController("python -m core.message_accept").run()
        self.ws_thread.start()

        # 等待键盘中断
        try:
            while True:
                self.restart()
                time.sleep(4)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """
        停止所有服务并清理资源。
        """
        end_time = datetime.datetime.now()
        logger.info(f"本次程序运行了 {end_time - self.start_time}, 正在停止所有进程...")
        logger.info("已停止")

    @simple_memory_release_decorator
    def restart(self) -> None:
        """
        重启 WebSocket 服务器和 FastAPI 应用。
        """
        if os.path.exists("restart.txt") and self.restart_value:
            with open("restart.txt", "r") as f:
                data = f.read().split(",")
            if data[0] == "stop":
                self.start_time = datetime.datetime.now()
                self.restart_value = False
                # 发出重启指令
                with open('restart_wsbot.txt', 'w') as f:
                    pass

                os.remove("restart.txt")
                logger.warning("正在重启服务...")
                while True:
                    time.sleep(1.0)
                    if not os.path.exists("restart_wsbot.txt"):
                        # 创建并运行 WebSocket 服务器线程
                        self.ws_thread = ThreadController("python -m core.message_accept").run()
                        self.ws_thread.start()
                        end_time = datetime.datetime.now()
                        with open('restart.txt', 'w') as f:
                            f.write(f"ok,{data[1]},{end_time - self.start_time}")
                            break
                logger.info("服务器重启完毕")
                self.restart_value = True
                del data, end_time

        if os.path.exists("restart_ignore.txt") and self.restart_value:
            self.restart_value = False
            os.remove("restart_ignore.txt")
            # 发出重启指令
            with open('restart_wsbot.txt', 'w') as f:
                pass
            while True:
                time.sleep(1.0)
                if not os.path.exists("restart_wsbot.txt"):
                    # 创建并运行 WebSocket 服务器线程
                    self.ws_thread = ThreadController("python -m core.message_accept").run()
                    self.ws_thread.start()
                    break

            self.restart_value = True


main = Application()
main.run()
