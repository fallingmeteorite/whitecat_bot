import yaml

from common.logging import logger

config: dict = {}


def load_config(file_path: str) -> None:
    """加载配置文件到全局变量 `config` 中。

    Args:
        file_path (str): 配置文件路径。
    """
    global config
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logger.debug("配置文件已成功加载")
    except FileNotFoundError:
        logger.error("配置文件未找到,请检查文件路径是否正确")
    except Exception as error:
        logger.error(f"加载配置文件时发生错误: {error}")


# 加载配置文件
load_config('config.yaml')
