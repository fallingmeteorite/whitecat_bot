from typing import Dict, Any

import yaml

from common.logging import logger

# Global configuration dictionary to store loaded configurations
config: Dict = {}


def load_config(file_path: str = None) -> bool:
    """
    Load the configuration file into the global variable `config`.

    Args:
        file_path (str): Path to the configuration file.

    Returns:
        bool: Whether the configuration file was successfully loaded.
    """
    if file_path is None:
        file_path = f'./config.yaml'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Safely load the YAML file using yaml.safe_load
            config.clear()
            config.update(yaml.safe_load(f) or {})
            logger.info("Configuration file loaded successfully")
            return True  # Return True indicating successful loading
    except Exception as error:
        logger.error(f"Unknown error occurred while loading configuration file: {error}")
    return False  # Return False indicating loading failure


def update_config(key: str, value: Any) -> bool:
    """
    Update a specific key-value pair in the global configuration dictionary.
    Changes are only applied in memory and do not persist to the file.

    Args:
        key (str): The key to update in the configuration dictionary.
        value: The new value to set for the specified key.

    Returns:
        bool: Whether the configuration was successfully updated in memory.
    """
    try:
        # Update the global config directly
        config[key] = value
        logger.info(f"Configuration updated in memory: {key} = {value}")
        return True  # Return True indicating successful update
    except Exception as error:
        logger.error(f"Unknown error occurred while updating configuration in memory: {error}")
    return False  # Return False indicating update failure


def save_config(file_path: str = None) -> bool:
    """
    Save the current in-memory configuration to the configuration file.

    Args:
        file_path (str): Path to the configuration file.

    Returns:
        bool: Whether the configuration was successfully saved to the file.
    """
    if file_path is None:
        file_path = f'./config.yaml'

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
        logger.info("Configuration saved to file successfully")
        return True
    except Exception as error:
        logger.error(f"Unknown error occurred while saving configuration to file: {error}")
    return False


# Load configuration file only when needed
def ensure_config_loaded():
    if not config and not load_config():
        logger.warning("Configuration file loading failed, the program may not run normally")


ensure_config_loaded()
