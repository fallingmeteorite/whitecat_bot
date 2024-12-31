import yaml

from common.logging import logger

# 全局配置字典，用于存储加载的配置
config: dict = {}


def load_config(file_path: str) -> bool:
    """
    加载配置文件到全局变量 `config` 中。

    Args:
        file_path (str): 配置文件路径。

    Returns:
        bool: 配置文件是否成功加载。
    """
    global config
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 使用 yaml.safe_load 安全地加载 YAML 文件
            config = yaml.safe_load(f)
            logger.debug("配置文件已成功加载")
            return True  # 返回 True 表示加载成功
    except FileNotFoundError:
        logger.error(f"配置文件未找到,请检查文件路径是否正确: {file_path}")
    except yaml.YAMLError as error:
        logger.error(f"配置文件解析错误: {error}")
    except Exception as error:
        logger.error(f"加载配置文件时发生未知错误: {error}")
    return False  # 返回 False 表示加载失败


# 加载配置文件
if not load_config('config.yaml'):
    logger.warning("配置文件加载失败,程序可能无法正常运行")
