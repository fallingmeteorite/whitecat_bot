import json
from typing import Dict, List, Optional

from common.config import config


class UserUsageTracker:
    """
    用户使用次数跟踪器类，负责管理用户使用次数的记录和检查。
    """

    def __init__(self, filename: str):
        """
        初始化用户使用次数跟踪器。

        Args:
            filename: 存储用户使用次数的文件路径。
        """
        self.filename = filename
        self.data: List[Dict[str, int]] = self.load_data()

    def load_data(self) -> List[Dict[str, int]]:
        """
        从文件中加载用户使用次数数据。

        Returns:
            List[Dict[str, int]]: 用户使用次数数据列表。
        """
        try:
            with open(self.filename, 'r') as file:
                return [json.loads(line) for line in file]
        except FileNotFoundError:
            return []

    def save_data(self) -> None:
        """
        将用户使用次数数据保存到文件中。
        """
        with open(self.filename, 'w') as file:
            for entry in self.data:
                file.write(json.dumps(entry) + '\n')

    def get_uid_count(self, uid: str) -> Optional[int]:
        """
        获取指定用户的使用次数。

        Args:
            uid: 用户 ID。

        Returns:
            Optional[int]: 用户使用次数，如果用户不存在则返回 None。
        """
        for entry in self.data:
            for item in entry.items():
                if str(item[0]) == str(uid):
                    return item[1]
        return None

    def use_detections(self, uid: str, gid: str) -> bool:
        """
        检查用户使用次数是否超过限制。

        Args:
            uid: 用户 ID。
            gid: 群组 ID。

        Returns:
            bool: 如果用户使用次数未超过限制，返回 True；否则返回 False。
        """
        if gid in config.get("use_restricted_groups", []):
            count = self.get_uid_count(uid)
            if count is None:
                self.data.append({uid: 1})
            elif count >= config.get("maximum_number_uses", 0):
                return False
            else:
                for i in range(len(self.data)):
                    for item in self.data[i].items():
                        if str(item[0]) == str(uid):
                            self.data[i][str(uid)] = count + 1
            self.save_data()
            return True
        return True


# 加载用户使用次数跟踪器
filename = config["user_use_file"]
tracker = UserUsageTracker(filename)
