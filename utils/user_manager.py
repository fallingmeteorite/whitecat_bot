import shelve
from typing import Dict, Optional

from common.config import config


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
        self.data: Dict[str, int] = self.load_data()

    def load_data(self) -> Dict[str, int]:
        """
        从文件中加载用户使用次数数据。

        Returns:
            Dict[str, int]: 用户使用次数数据字典，键为用户 ID，值为使用次数。
        """
        try:
            with shelve.open(self.filename) as db:
                return {k: v for k, v in db.items()}
        except FileNotFoundError:
            return {}

    def save_data(self) -> None:
        """
        将用户使用次数数据保存到文件中。
        """
        with shelve.open(self.filename) as db:
            for k, v in self.data.items():
                db[k] = v

    def get_uid_count(self, uid: str) -> Optional[int]:
        """
        获取指定用户的使用次数。

        Args:
            uid: 用户 ID。

        Returns:
            Optional[int]: 用户使用次数，如果用户不存在则返回 None。
        """
        return self.data.get(uid)

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
            max_uses = config.get("maximum_number_uses", 0)

            if count is None:
                self.data[uid] = 1
            elif count >= max_uses:
                return False
            else:
                self.data[uid] = count + 1

            self.save_data()
            return True
        return True


# 加载用户使用次数跟踪器
filename = config["user_use_file"]
tracker = UserUsageTracker(filename)
