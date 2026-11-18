import inspect
from typing import get_origin, get_args, List
import xarray as xr

REGISTERED_OPERATIONS = {}

def galaxy_op(name=None, description=""):
    def decorator(func):
        func_name = name or func.__name__
        REGISTERED_OPERATIONS[func_name] = {
            "func": func,
            "name": func_name,
            "description": description or func.__doc__ or "",
            "signature": inspect.signature(func)
        }
        return func
    return decorator
