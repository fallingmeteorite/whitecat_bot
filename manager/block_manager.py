from common.config import config


def ban_filter(uid, gid, command):
    # 全局不可用群和人
    if gid in config["ban_gid_list"] or uid in config["ban_uid_list"]:  # 列表
        return False

    # 过滤器可用群中不可用人
    if gid in config["valid_gids_list"]:  # 列表
        if uid in list(config["ban_valid_uids"].keys()):  # 字典
            command_all = [i for k in list(config["ban_valid_uids"].values()) for i in k]  # 列表
            if command in command_all or command == "all":
                return False
            else:
                return True
        else:
            return True
    return False


def ban_plugin(uid, gid, command):
    # 全局不可用群和人
    if gid in config["ban_gid_list"] or uid in config["ban_uid_list"]:  # 列表
        return False

    # 插件可用群中的不可用人
    if gid in config["plugin_gids_list"]:  # 列表
        if uid in list(config["ban_plugin_uids"].keys()):  # 字典
            command_all = [i for k in list(config["ban_plugin_uids"].values()) for i in k]  # 列表
            if command in command_all or command == "all":
                return False
            else:
                return True
        else:
            return True

    return False
