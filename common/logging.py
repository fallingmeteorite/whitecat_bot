import os
import sys
import weakref
from loguru import logger as loguru_logger

# 获取当前工作目录
current_dir = os.getcwd()
log_dir = os.path.join(current_dir, 'log')

# 如果日志目录不存在，则创建之
os.makedirs(log_dir, exist_ok=True)

# 默认日志格式（带颜色）
default_format: str = (
    "<g>{time:MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}</u></c> | "
    "{message}"
)

# 不带颜色的备用日志格式
plain_format: str = (
    "{time:MM-DD HH:mm:ss} "
    "[{level}] "
    "{name} | "
    "{message}"
)

# 默认日志等级
LOG_LEVEL = "INFO"

# 使用弱引用存储日志记录器
_logger_ref = weakref.ref(loguru_logger)

try:
    # 使用绝对路径设置日志文件路径
    log_file_path = os.path.join(log_dir, 'data_{time:YYYY_MM_DD}.log')

    # 添加日志文件输出
    _logger_ref().add(
        log_file_path,
        rotation='12 hours',  # 每 12 小时轮换一次日志文件
        retention='7 days',  # 保留最近 7 天的日志文件
        level=LOG_LEVEL,  # 设置日志等级
        enqueue=True,  # 启用线程安全
        format=default_format,  # 使用带颜色的日志格式
        compression="zip",  # 压缩旧日志文件
    )
except Exception as e:
    # 如果日志文件设置失败，输出错误信息并使用标准输出作为备份
    print(f"设置日志时发生错误: {e}\n"
          f"可能的原因: 检查日志目录权限，确保路径有效，检查 Loguru 配置。", file=sys.stderr)
    # 添加标准错误输出作为备份
    _logger_ref().add(sys.stderr, level=LOG_LEVEL, format=plain_format)

# 日志记录器对象
logger = _logger_ref()

# 在程序结束时关闭日志记录器
import atexit
atexit.register(lambda: _logger_ref().remove())
