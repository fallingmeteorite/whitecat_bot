from typing import Dict, Set
from config.config import config


def is_command_allowed(uid: int, gid: int, command: str, gids_key: str, ban_key: str) -> bool:
    """
    检查是否允许在指定群组中使用指定命令。

    Args:
        uid: 用户 ID。
        gid: 群组 ID。
        command: 命令名称。
        gids_key: 配置中群组列表的键名。
        ban_key: 配置中禁止列表的键名。

    Returns:
        bool: 如果允许使用命令，返回 True；否则返回 False。
    """
    # 检查群组是否在指定的群组列表中
    valid_gids: Set[int] = config.get(gids_key, set())
    if gid not in valid_gids:
        return False

    # 检查用户或群组是否被禁止使用该命令
    ban_dict: Dict[int, Set[str]] = config.get(ban_key, {})
    allowed = not is_banned(ban_dict, uid, gid, command)

    # 显式删除不再使用的变量
    del valid_gids
    del ban_dict

    return allowed


def is_banned(ban_dict: Dict[int, Set[str]], uid: int, gid: int, command: str) -> bool:
    """
    检查用户或群组是否被禁止使用指定命令。

    Args:
        ban_dict: 禁止列表字典，键为群组 ID 或用户 ID，值为禁止的命令列表。
        uid: 用户 ID。
        gid: 群组 ID。
        command: 命令名称。

    Returns:
        bool: 如果被禁止，返回 True；否则返回 False。
    """
    # 检查群组是否在禁止列表中
    if gid in ban_dict:
        banned_commands = ban_dict[gid]
        if command in banned_commands or "all" in banned_commands:
            return True

    # 检查用户是否在禁止列表中
    if uid in ban_dict:
        banned_commands = ban_dict[uid]
        if command in banned_commands or "all" in banned_commands:
            return True

    return False


def ban_filter(uid: int, gid: int, command: str) -> bool:
    """
    检查过滤器是否允许在指定群组中使用指定命令。

    Args:
        uid: 用户 ID。
        gid: 群组 ID。
        command: 命令名称。

    Returns:
        bool: 如果允许使用命令，返回 True；否则返回 False。
    """
    result = is_command_allowed(uid, gid, command, "valid_gids_list", "ban_valid_uids")

    # 显式删除不再使用的变量
    del uid
    del gid
    del command

    return result


def ban_plugin(uid: int, gid: int, command: str) -> bool:
    """
    检查插件是否允许在指定群组中使用指定命令。

    Args:
        uid: 用户 ID。
        gid: 群组 ID。
        command: 命令名称。

    Returns:
        bool: 如果允许使用命令，返回 True；否则返回 False。
    """
    result = is_command_allowed(uid, gid, command, "plugin_gids_list", "ban_plugin_uids")

    # 显式删除不再使用的变量
    del uid
    del gid
    del command

    return result
