import asyncio
import functools
import time
from collections.abc import Awaitable
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Callable, Optional, ParamSpec, TypeVar, cast, overload


def format_hhmmss(s: float):
    delta = timedelta(seconds=s)
    hours = delta.days * 24 + delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"


T = TypeVar("T")
P = ParamSpec("P")


def throttle(_func=None, *, delay=1):
    """Will return `None` if called within window"""

    def decorate(func: Callable[P, T]):
        last_called: float | None = None
        lock = asyncio.Lock()

        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs):
            if asyncio.iscoroutinefunction(func):
                raise Exception()
            nonlocal last_called
            now = time.time()
            result = None
            if not last_called or now - last_called > delay:
                result = func(*args, **kwargs)
                last_called = now
            return cast(T, result)

        @functools.wraps(func)
        async def wrapped_async(*args: P.args, **kwargs: P.kwargs):
            if not asyncio.iscoroutinefunction(func):
                raise Exception()
            async with lock:
                nonlocal last_called
                now = time.time()
                result = None
                if not last_called or now - last_called > delay:
                    result = await func(*args, **kwargs)
                    last_called = now
            return cast(T, result)

        if asyncio.iscoroutinefunction(func):
            return wrapped_async
        else:
            return wrapped

    if _func:
        # Decorator called without arguments: _func is passed
        # We apply and return the decorated function (with default values)
        return decorate(_func)
    else:
        # Decorator called with arguments: _func will be None
        # We return the decorator (as a closure), which will then be applied to the function
        return decorate
