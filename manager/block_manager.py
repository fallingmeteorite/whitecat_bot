from common.config import config


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
    # 检查群组是否在有效群组列表中
    if gid in config.get("valid_gids_list", []):
        return check_ban(config.get("ban_valid_uids", {}), uid, gid, command)
    return False


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
    # 检查群组是否在插件可用群组列表中
    if gid in config.get("plugin_gids_list", []):
        return check_ban(config.get("ban_plugin_uids", {}), uid, gid, command)
    return False


def check_ban(ban_dict: dict, uid: int, gid: int, command: str) -> bool:
    """
    检查用户或群组是否被禁止使用指定命令。

    Args:
        ban_dict: 禁止列表字典，键为群组 ID 或用户 ID，值为禁止的命令列表。
        uid: 用户 ID。
        gid: 群组 ID。
        command: 命令名称。

    Returns:
        bool: 如果允许使用命令，返回 True；否则返回 False。
    """
    # 检查群组是否在禁止列表中
    if gid in ban_dict:
        banned_commands = ban_dict[gid]
        if command in banned_commands or "all" in banned_commands:
            return False

    # 检查用户是否在禁止列表中
    if uid in ban_dict:
        banned_commands = ban_dict[uid]
        if command in banned_commands or "all" in banned_commands:
            return False

    return True
