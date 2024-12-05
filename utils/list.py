def in_list(li: list, *args):
    for _ in args:
        if _ in li:
            return True

    return False
