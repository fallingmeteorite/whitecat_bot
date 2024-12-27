from adapter_process.qq import handle_message


class AdapterManager:
    def __init__(self, message):
        self.message = message

    def start(self):
        message = handle_message(self.message)
        if message is not None:
            return message

        # 不符合就返回None
        return None, None, None, None
