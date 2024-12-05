from typing import Optional


def try_int(i: Optional[int], default=0):
    try:
        return int(i)
    except:
        return default
