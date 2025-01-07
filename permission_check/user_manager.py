import json
from typing import Dict, Optional

from config.config import config


class UserUsageTracker:
    __slots__ = ['filename', 'data']

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
        self.data: Dict[str, int] = self._load_data()

    def _load_data(self) -> Dict[str, int]:
        """
        从文件中加载用户使用次数数据。

        Returns:
            Dict[str, int]: 用户使用次数数据字典，键为用户 ID，值为使用次数。
        """
        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_data(self) -> None:
        """
        将用户使用次数数据保存到文件中。
        """
        with open(self.filename, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def get_usage_count(self, uid: str) -> Optional[int]:
        """
        获取指定用户的使用次数。

        Args:
            uid: 用户 ID。

        Returns:
            Optional[int]: 用户使用次数，如果用户不存在则返回 None。
        """
        return self.data.get(uid)

    def can_use_detection(self, uid: str, gid: str) -> bool:
        """
        检查用户使用次数是否超过限制。

        Args:
            uid: 用户 ID。
            gid: 群组 ID。

        Returns:
            bool: 如果用户使用次数未超过限制，返回 True；否则返回 False。
        """
        # 检查群组是否在使用限制列表中
        if gid not in config.get("use_restricted_groups", []):
            return True

        # 获取用户当前使用次数和最大允许次数
        current_count = self.get_usage_count(uid)
        max_uses = config.get("maximum_number_uses", 0)

        # 如果用户不存在于记录中，初始化使用次数为 1
        if current_count is None:
            self.data[uid] = 1
            self._save_data()
            return True

        # 检查使用次数是否超过限制
        if current_count >= max_uses:
            return False

        # 增加使用次数并保存数据
        self.data[uid] = current_count + 1
        self._save_data()
        return True


# 加载用户使用次数跟踪器
filename = config["user_use_file"]
tracker = UserUsageTracker(filename)
