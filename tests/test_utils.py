import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from transcription_bot.handlers.utils import athrottle


async def repeat_async(
    func: Callable[[], Awaitable[Any]],
    times: int,
    interval: float = 0,
):
    """Repeatedly call an async function, optionally with a delay between invocations."""
    for _ in range(times):
        await func()
        if interval:
            await asyncio.sleep(interval)


@pytest.mark.asyncio()
async def test_throttle_return_result():
    """Check that a function's result is None if called within the window, and not None otherwise."""
    count = 0
    delay = 0.1

    @athrottle(delay=delay)
    async def throttle():
        nonlocal count
        count += 1
        return count

    assert await throttle() == 1
    for _ in range(2):
        assert await throttle() is None

    # Wait for the window to be over
    await asyncio.sleep(delay)

    assert await throttle() == 2


@pytest.mark.asyncio()
async def test_throttle_async_default_delay():
    """Test that the default delay works."""
    count = 0

    @athrottle
    async def throttle_default():
        nonlocal count
        count += 1

    await repeat_async(throttle_default, 10)
    assert count == 1


@pytest.mark.asyncio()
async def test_throttle_async_custom_delay():
    """Test that a custom delay works."""
    count = 0

    @athrottle(delay=0.2)
    async def throttle_custom():
        nonlocal count
        count += 1

    # We call 4 times with 0.1 interval: function will only fire twice total (2nd and 4th calls ignored.)
    await repeat_async(throttle_custom, 4, 0.1)
    assert count == 2


@pytest.mark.asyncio()
async def test_throttle_async_with_await():
    """
    Tests that `throttle` works when the async function to be wrapped contains an await statement.
    """
    count = 0

    @athrottle(delay=3)
    async def foo():
        nonlocal count
        count += 1
        await asyncio.sleep(0)

    async with asyncio.TaskGroup() as tg:
        for _ in range(3):
            tg.create_task(foo())

    assert count == 1
