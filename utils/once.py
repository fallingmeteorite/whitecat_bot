class Once:
    def __init__(self):
        self.once_run = set()

    def if_once(self, s: str):
        if s in self.once_run:
            return False
        else:
            self.once_run.add(s)
            return True


def create_once():
    return Once()
