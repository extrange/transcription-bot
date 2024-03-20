import asyncio
import random
import string
import time
from pathlib import Path

import pytest
import uvloop
from conftest import (BOT_USERNAME, ME_USERNAME, OTHER_USERNAME, ClientGroup,
                      get_random_string)
from utils import (helper_test_transcription_for_file, test_files, wait_for_async,
                   wait_for_new_messages)

from transcriptionbot.bot.handlers import _welcome_message

loop: asyncio.AbstractEventLoop

pytestmark = pytest.mark.asyncio(scope="session")


async def test_event_loop_policy_is_uvloop():
    # Save current loop for the next test
    global loop
    loop = asyncio.get_running_loop()
    assert isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy)


async def test_same_loop_used_for_module():
    global loop
    assert asyncio.get_running_loop() == loop


async def test_bot_welcome_message(clients: ClientGroup):
    await clients.me.send_message(BOT_USERNAME, "test")

    async def check_message_equal_to_welcome() -> bool:
        messages = await clients.me.get_messages(BOT_USERNAME)
        return messages[0].text == _welcome_message

    await wait_for_async(check_message_equal_to_welcome, 3)

# TODO https://docs.pytest.org/en/7.1.x/how-to/parametrize.html
async def test_audio_ogg(clients: ClientGroup, tmp_path: Path):
    await helper_test_transcription_for_file(clients.me, test_files.short_ogg, tmp_path)


async def test_me_handle_cancel(clients: ClientGroup): ...


async def test_other_handle_cancel(clients: ClientGroup): ...


async def test_handle_audio_file(clients: ClientGroup): ...


async def test_handle_video(clients: ClientGroup): ...


async def test_other_handle_voice_and_notify_me(clients: ClientGroup): ...


async def test_other_invalid_audio_and_notify_me(clients: ClientGroup): ...
