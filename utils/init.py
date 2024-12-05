import inspect
from typing import Type, Dict, Any


def class_init(cls: Type, kws: Dict[str, Any]):
    init_params = inspect.signature(cls.__init__).parameters
    cls_kwargs = {k: v for k, v in kws.items() if k in init_params}
    return cls(**cls_kwargs)
