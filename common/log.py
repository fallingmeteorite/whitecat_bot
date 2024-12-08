"""该模块定义了通用的日志记录Logger。

默认信息:

- 格式: `%(asctime)s %(levelname)s %(name)s: %(message)s`
- 等级: `INFO` ，根据 `config.log_level` 配置改变
- 输出: 输出至log文件夹下

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

# 默认日志等级
LOG_LEVEL = "INFO"

try:
    # 使用相对路径
    log_file_path = os.path.join(log_dir, 'data_{time:YYYY_DD}.log')

    # 设置日志等级和格式
    logger.add(
        log_file_path,
        rotation='12 hours',
        level=LOG_LEVEL,
        enqueue=True,
        format="<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>{name}</u></c> | {message}",
    )
except Exception as e:
    print(f"Error setting up logging: {e}", file=sys.stderr)
    # 如果设置失败, 使用标准输出作为备份
    logger.add(sys.stderr, level=LOG_LEVEL, format="{time:MM-DD HH:mm:ss} [{level}] {name} | {message}")

# 导出日志记录器对象
__all__ = ['logger']