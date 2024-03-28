import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from transcriptionbot.bot.utils import throttle


def repeat(func: Callable[[], Any], times: int, interval: float = 0):
    for _ in range(times):
        func()
        if interval:
            time.sleep(interval)


async def repeat_async(
    func: Callable[[], Awaitable[Any]], times: int, interval: float = 0
):
    for _ in range(times):
        await func()
        if interval:
            await asyncio.sleep(interval)


def test_throttle_default_delay():

    count = 0

    @throttle
    def throttle_default():
        nonlocal count
        count += 1

    repeat(throttle_default, 10)

    assert count == 1

def test_throttle_custom_delay():
    count = 0

    @throttle(delay=2)
    def throttle_custom():
        nonlocal count
        count += 1

    repeat(throttle_custom, 5, 1)
    assert count == 3


@pytest.mark.asyncio
async def test_throttle_async_default_delay():
    count = 0

    @throttle
    async def throttle_default():
        nonlocal count
        count += 1
    
    await repeat_async(throttle_default, 10)
    assert count == 1

@pytest.mark.asyncio
async def test_throttle_async_custom_delay():
    count = 0

    @throttle(delay=2)
    async def throttle_custom():
        nonlocal count
        count += 1
    
    await repeat_async(throttle_custom, 5, 1)
    assert count == 3

@pytest.mark.asyncio
async def test_throttle_async_with_await():
    """
    Tests that `throttle` works when the async function to be wrapped contains an await statement.
    """
    count = 0

    @throttle(delay=3)
    async def foo():
        nonlocal count
        count += 1
        await asyncio.sleep(0)
    
    async with asyncio.TaskGroup() as tg:
        for _ in range(3):
            tg.create_task(foo())
    
    assert count == 1


