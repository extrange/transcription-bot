import asyncio
import functools
import time
from collections.abc import Callable, Coroutine
from datetime import timedelta
from typing import Any, overload


def format_hhmmss(s: float) -> str:
    """Format seconds into HH:MM:SS format."""
    delta = timedelta(seconds=s)
    hours = delta.days * 24 + delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"


type Coro[T] = Coroutine[Any, Any, T]
type CallableCoro[**P, T] = Callable[P, Coro[T]]
type WrappedDeco[**P, T] = Callable[
    [Callable[P, Coro[T]]],
    Callable[P, Coro[T | None]],
]


@overload
def athrottle[**P, R](*, delay: float = 1) -> WrappedDeco[P, R]: ...


@overload
def athrottle[**P, T](
    _func: Callable[P, Coro[T]],
    *,
    delay: float = 1,
) -> Callable[P, Coro[T | None]]: ...


def athrottle[**P, T](
    _func: Callable[P, Coro[T]] | None = None,
    *,
    delay: float = 1,
) -> Callable[P, Coro[T | None]] | WrappedDeco[P, T]:
    """
    Decorate a sync or async function with throttle.

    Returns `None` if called within window.
    """

    def decorate(
        func: Callable[P, Coro[T]],
    ) -> Callable[P, Coro[T | None]]:
        last_called: float | None = None
        lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapped_async(*args: P.args, **kwargs: P.kwargs) -> T | None:
            # The lock is necessary to ensure that tasks created at the same time don't simultaneously modify last_called
            async with lock:
                nonlocal last_called
                now = time.time()
                result = None
                if not last_called or now - last_called > delay:
                    result = await func(*args, **kwargs)
                    last_called = now
            return result

        return wrapped_async

    if _func:
        # Decorator called without arguments: _func is passed
        # We apply and return the decorated function (with default values)
        return decorate(_func)
    # Decorator called with arguments: _func will be None
    # We return the decorator (as a closure), which will then be applied to the function
    return decorate
