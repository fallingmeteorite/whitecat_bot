"""该模块定义了通用的日志记录 Logger。

默认信息:
- 格式: `<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>{name}</u></c> | {message}`
- 等级: `INFO`，根据 `config.log_level` 配置改变
- 输出: 输出至 `log` 文件夹下

用法:
```python
from log import logger
```
"""

import os
import sys
from loguru import logger

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

try:
    # 使用绝对路径设置日志文件路径
    log_file_path = os.path.join(log_dir, 'data_{time:YYYY_MM_DD}.log')

    # 添加日志文件输出
    logger.add(
        log_file_path,
        rotation='12 hours',  # 每 12 小时轮换一次日志文件
        retention='7 days',   # 保留最近 7 天的日志文件
        level=LOG_LEVEL,      # 设置日志等级
        enqueue=True,         # 启用线程安全
        format=default_format,  # 使用带颜色的日志格式
        compression="zip",    # 压缩旧日志文件
    )
except Exception as e:
    # 如果日志文件设置失败，输出错误信息并使用标准输出作为备份
    print(f"Error setting up logging: {e}", file=sys.stderr)
    logger.add(sys.stderr, level=LOG_LEVEL, format=plain_format)

# 日志记录器对象
logger = logger
"""日志记录器对象。

默认信息:
- 格式: `<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>{name}</u></c> | {message}`
- 等级: `INFO`，根据 `config.log_level` 配置改变
- 输出: 输出至 `log` 文件夹下
"""
