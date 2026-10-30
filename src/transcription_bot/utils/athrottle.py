"""Throttle async function calls."""

import asyncio
import functools
import time
from collections.abc import Callable, Coroutine
from typing import Any, overload


@overload
def athrottle[**P, R](
    *,
    delay: float = 1,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R | None]]
]: ...


@overload
def athrottle[**P, R](
    func: Callable[P, Coroutine[Any, Any, R]],
    *,
    delay: float = 1,
) -> Callable[P, Coroutine[Any, Any, R | None]]: ...


def athrottle[**P, R](
    func: Callable[P, Coroutine[Any, Any, R]] | None = None,
    *,
    delay: float = 1,
) -> (
    Callable[P, Coroutine[Any, Any, R | None]]
    | Callable[
        [Callable[P, Coroutine[Any, Any, R]]],
        Callable[P, Coroutine[Any, Any, R | None]],
    ]
):
    """
    Throttle an async function, returning `None` for calls within `delay` seconds of the last one.

    Use as `@athrottle(delay=3)`, or as `@athrottle` for the default delay.
    """

    def _decorate(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R | None]]:
        last_called: float | None = None
        lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | None:
            # The lock stops tasks created at the same time from racing on `last_called`
            async with lock:
                nonlocal last_called
                now = time.monotonic()

                if last_called is not None and now - last_called <= delay:
                    return None

                result = await func(*args, **kwargs)
                last_called = now

            return result

        return wrapped

    if func is None:
        return _decorate

    return _decorate(func)
