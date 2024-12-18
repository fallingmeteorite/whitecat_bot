from common.config import config


def ban_filter(uid, gid, command):
    # 过滤器可用群
    if gid in config["valid_gids_list"]:  # 列表

        if gid in list(config["ban_valid_uids"].keys()): # 字典
            command_all = config["ban_valid_uids"][gid] # 列表
            if command in command_all or "all" in command_all:
                return False
            else:
                return True

        
        if uid in list(config["ban_valid_uids"].keys()): # 字典
            command_all = config["ban_valid_uids"][gid]
            if command in command_all or "all" in command_all:
                return False
            else:
                return True
            
        else:
            return True
    return False
            
def ban_plugin(uid, gid, command):  
    # 插件可用群中
    if gid in config["plugin_gids_list"]:  # 列表
        if gid in list(config["ban_plugin_uids"].keys()): # 字典
            command_all = config["ban_plugin_uids"][gid] # 列表
            if command in command_all or "all" in command_all:
                return False
            else:
                return True
            
        if uid in list(config["ban_plugin_uids"].keys()): # 字典
            command_all = config["ban_plugin_uids"][uid] # 列表
            if command in command_all or "all" in command_all:
                return False
            else:
                return True
        else:
            return True
    
    return False
