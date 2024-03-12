from datetime import timedelta
from typing import Callable
import time
import functools


def format_hhmmss(s: float):
    delta = timedelta(seconds=s)
    hours = delta.days * 24 + delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def throttle(_func=None, *, delay=1):
    """Will not work with async functions"""
    def decorate(func: Callable):
        t: float | None = None

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            nonlocal t
            now = time.time()
            result = None
            if not t or now - t > delay:
                result = func(*args, **kwargs)
                t = now
            return result

        return wrapped

    if _func:
        # Decorator called without arguments: _func is defined
        # We apply and return the decorated function (with default values)
        return decorate(_func)
    else:
        # Decorator called with arguments: _func will be None
        # We return the decorator (as a closure), which will then be applied to the function
        return decorate
