import pytest
from transcriptionbot.main import main
from telethon import TelegramClient
import asyncio
import uvloop
import uvloop

# Reuse the same event loop for the whole module
pytestmark = pytest.mark.asyncio(scope="module")

loop: asyncio.AbstractEventLoop


async def test_event_loop_policy_is_uvloop():
    global loop
    loop = asyncio.get_running_loop()
    assert isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy)

async def test_same_loop_used_for_module():
    global loop
    assert asyncio.get_running_loop() == loop
