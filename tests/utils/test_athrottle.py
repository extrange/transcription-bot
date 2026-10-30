import asyncio

from transcription_bot.utils.athrottle import athrottle


async def test_runs_first_call_and_skips_immediate_repeat():
    calls: list[int] = []

    @athrottle(delay=0.01)
    async def record(value: int) -> int:
        calls.append(value)
        return value

    assert await record(1) == 1
    assert await record(2) is None
    assert calls == [1]


async def test_runs_again_once_delay_has_elapsed():
    calls: list[int] = []

    @athrottle(delay=0.01)
    async def record(value: int) -> int:
        calls.append(value)
        return value

    assert await record(1) == 1
    await asyncio.sleep(0.02)
    assert await record(2) == 2
    assert calls == [1, 2]


async def test_usable_without_arguments():
    @athrottle
    async def get_value() -> str:
        return "value"

    assert await get_value() == "value"
    assert await get_value() is None
