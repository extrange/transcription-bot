import asyncio
from pathlib import Path
from typing import cast

import pytest
import uvloop
from conftest import BOT_USERNAME, ClientGroup
from helpers import (_TestFile, helper_test_transcription_for_file, test_files,
                     wait_for_async, wait_for_new_messages)
from telethon import events
from telethon.custom import Message

from transcriptionbot.bot.handlers import _welcome_message

loop: asyncio.AbstractEventLoop

pytestmark = pytest.mark.asyncio(scope="session")


@pytest.mark.skip
async def test_event_loop_policy_is_uvloop():
    # Save current loop for the next test
    global loop
    loop = asyncio.get_running_loop()
    assert isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy)


@pytest.mark.skip
async def test_same_loop_used_for_telethon(clients: ClientGroup):
    global loop
    assert loop == clients.me.loop
    assert loop == clients.other.loop
    assert loop == clients.bot.loop


@pytest.mark.skip
async def test_bot_welcome_message(clients: ClientGroup):
    async with clients.me.conversation(BOT_USERNAME, timeout=5) as conv:
        await conv.send_message("/start")
        resp: Message = await conv.get_response()
        assert _welcome_message in cast(str, resp.raw_text)


@pytest.mark.skip
@pytest.mark.parametrize(
    "test_file", [test_files.short_ogg, test_files.video_mp4, test_files.video_webm]
)
async def test_transcriptions(
    clients: ClientGroup, tmp_path: Path, test_file: _TestFile
):
    await helper_test_transcription_for_file(
        clients.me, test_file, tmp_path, timeout=90
    )


@pytest.mark.skip
@pytest.mark.parametrize("test_file", [test_files.short_ogg])
async def test_other_transcribe_audio_and_notify_me(
    clients: ClientGroup, tmp_path: Path, test_file: _TestFile
):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            helper_test_transcription_for_file(
                clients.other, test_file, tmp_path, timeout=90
            )
        )

        me_msgs_task = tg.create_task(wait_for_new_messages(clients.me, 2, timeout=90))

    me_msgs = me_msgs_task.result()
    assert me_msgs[1].file is not None


@pytest.mark.skip
async def test_locking_multiple_requests(clients: ClientGroup):
    with test_files.long_ogg.path.open("rb") as f:
        await clients.other.send_file(BOT_USERNAME, f)

    # Wait until transcription starts for the previous client
    started_transcribing = False

    async def set_started_transcribing(message: Message):
        nonlocal started_transcribing
        if "transcribing" in cast(str, message.raw_text).lower():
            started_transcribing = True

    async def check_started_transcribing():
        return started_transcribing

    try:
        clients.other.add_event_handler(
            set_started_transcribing, events.MessageEdited(incoming=True)
        )
        await wait_for_async(check_started_transcribing, timeout=60)
    finally:
        clients.other.remove_event_handler(set_started_transcribing)

    # Now send short test file
    with test_files.short_ogg.path.open("rb") as f:
        await clients.me.send_file(BOT_USERNAME, f)

    is_locked = False

    async def set_is_locked(message: Message):
        nonlocal is_locked
        if "waiting" in cast(str, message.raw_text).lower():
            is_locked = True

    async def check_is_locked():
        return is_locked

    try:
        clients.me.add_event_handler(set_is_locked, events.MessageEdited(incoming=True))
        await wait_for_async(check_is_locked, timeout=60)
        await wait_for_new_messages(clients.me, 2, timeout=60)
    finally:
        clients.me.remove_event_handler(set_is_locked)


async def test_other_invalid_audio_and_notify_me(clients: ClientGroup):
    with test_files.invalid_ogg.open("rb") as f:
        await clients.other.send_file(BOT_USERNAME, f)

    messages = await wait_for_new_messages(clients.me, 2, timeout=60)

    assert "error" in cast(str, messages[1].raw_text).lower()
