import asyncio
from pathlib import Path
from typing import cast

import pytest
import uvloop
from conftest import ClientGroup
from helpers import (
    _TestFile,
    helper_test_transcription_for_file,
    test_files,
    wait_for_async,
    wait_for_new_messages,
)
from telethon import events, errors
from telethon.custom import Message

from transcriptionbot.bot.handlers import _welcome_message


async def test_same_loop_used_for_telethon(clients: ClientGroup):
    loop = asyncio.get_running_loop()
    assert loop == clients.me.client.loop
    assert loop == clients.other.client.loop
    assert loop == clients.bot.client.loop


async def test_bot_welcome_message(clients: ClientGroup):
    async with clients.me.client.conversation(clients.bot.username, timeout=5) as conv:
        await conv.send_message("/start")
        resp: Message = await conv.get_response()
        assert _welcome_message in cast(str, resp.raw_text)


@pytest.mark.parametrize("test_file", [test_files.video_mp4, test_files.video_webm])
async def test_transcriptions(
    clients: ClientGroup, tmp_path: Path, test_file: _TestFile
):
    await helper_test_transcription_for_file(
        clients.me.client, clients.bot.username, test_file, tmp_path, timeout=90
    )


@pytest.mark.parametrize("test_file", [test_files.short_ogg])
async def test_other_transcribe_audio_and_notify_me(
    clients: ClientGroup, tmp_path: Path, test_file: _TestFile
):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            helper_test_transcription_for_file(
                clients.other.client, clients.bot.username, test_file, tmp_path, timeout=90
            )
        )

        me_msgs_task = tg.create_task(wait_for_new_messages(clients.me.client, 2, timeout=90))

    me_msgs = me_msgs_task.result()
    assert me_msgs[1].file is not None


async def test_other_invalid_audio_and_notify_me(clients: ClientGroup):
    with test_files.invalid_ogg.open("rb") as f:
        await clients.other.client.send_file(clients.bot.username, f)
        

    messages = await wait_for_new_messages(clients.me.client, 2, timeout=60)

    assert "error" in cast(str, messages[1].raw_text).lower()


async def test_locking_multiple_requests(clients: ClientGroup):
    """Needs to be the last test as event loop is cut off abruptly"""
    with test_files.long_ogg.path.open("rb") as f:
        await clients.other.client.send_file(clients.bot.username, f)

    # Wait until transcription starts for the previous client
    started_transcribing = False

    async def set_started_transcribing(message: Message):
        nonlocal started_transcribing
        if "transcribing" in cast(str, message.raw_text).lower():
            started_transcribing = True

    async def check_started_transcribing():
        return started_transcribing

    try:
        clients.other.client.add_event_handler(
            set_started_transcribing, events.MessageEdited(incoming=True)
        )
        await wait_for_async(check_started_transcribing, timeout=60)
    finally:
        clients.other.client.remove_event_handler(set_started_transcribing)

    # Now send short test file
    with test_files.short_ogg.path.open("rb") as f:
        await clients.me.client.send_file(clients.bot.username, f)

    is_locked = False

    async def set_is_locked(message: Message):
        nonlocal is_locked
        if "waiting" in cast(str, message.raw_text).lower():
            is_locked = True

    async def check_is_locked():
        return is_locked

    try:
        clients.me.client.add_event_handler(set_is_locked, events.MessageEdited(incoming=True))
        await wait_for_async(check_is_locked, timeout=60)
        await wait_for_new_messages(clients.me.client, 2, timeout=60)
    finally:
        clients.me.client.remove_event_handler(set_is_locked)
