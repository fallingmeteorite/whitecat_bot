import json
from common.config import config



class UserUsageTracker:
    def __init__(self, filename):
        self.filename = filename

    # 实时加载文件
    def load_data(self):
        try:
            with open(self.filename, 'r') as file:
                return [json.loads(line) for line in file]
        except FileNotFoundError:
            return []

    # 保存文件
    def save_data(self, data):
        with open(self.filename, 'w') as file:
            for entry in data:
                file.write(json.dumps(entry) + '\n')

    # 获取用户的使用次数,没有这个用户就返回None
    def get_uid_count(self, uid):
        data = self.load_data()
        for entry in data:
            for item in entry.items():
                if str(item[0]) == str(uid):
                    return item[1]
        return None

    # 返回这个用户使用是否超过上线,是则返回False阻止功能调用,没有则返回True
    def use_detections(self, uid, gid):
        if gid in config["use_restricted_groups"]:
            data = self.load_data()
            count = self.get_uid_count(uid)
            if count is None:
                data.append({uid: 1})
            elif count >= config["maximum_number_uses"]:
                return False
            else:
                for i in range(len(data)):
                    for item in data[i].items():
                        if str(item[0]) == str(uid):
                            data[i][str(uid)] = count + 1
            self.save_data(data)
            return True
        return True


filename = config["user_use_file"]
tracker = UserUsageTracker(filename)
