import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from conftest import BOT_USERNAME
from telethon import TelegramClient, events
from telethon.custom import Message

_TEST_FILES_DIR = Path(__file__).parent / "test_files"


class _TestFile:
    def __init__(self, filename: str) -> None:
        self.path = _TEST_FILES_DIR / filename
        self.txt = (_TEST_FILES_DIR / f"{self.path.stem}.txt").read_text()
        self.srt = (_TEST_FILES_DIR / f"{self.path.stem}.srt").read_text()

    def compare_txt(self, s: str):
        return s == self.txt

    def compare_srt(self, s: str):
        return s == self.srt


class _TestFiles:
    short_ogg = _TestFile("short_ogg.ogg")
    long_ogg = _TestFile("long_ogg.ogg")
    video_mp4 = _TestFile("video_mp4.mp4")
    video_webm = _TestFile("video_webm.webm")
    invalid_ogg = _TEST_FILES_DIR / "invalid_ogg.ogg"

    @classmethod
    def __iter__(cls):
        for attr in cls.__dict__:
            value = getattr(cls, attr)
            if isinstance(value, _TestFile):
                yield value


test_files = _TestFiles()


async def wait_for_async(condition: Callable[[], Awaitable[bool]], timeout=10):
    """
    Wait until a condition is true, otherwise raise an exception.
    """
    now = time.time()
    while not await condition():

        if time.time() - now > timeout:
            raise TimeoutError(f"Exceeded {timeout}s")
        await asyncio.sleep(1)


async def wait_for_new_messages(client: TelegramClient, num: int, timeout=10):
    """
    Wait until `num` new messages are received, from now.

    Returns the new messages, from oldest to newest.
    """
    messages: list[Message] = []

    async def on_message(message: Message):
        messages.append(message)

    async def condition():
        return len(messages) >= num

    try:
        client.add_event_handler(on_message, events.NewMessage(incoming=True))

        await wait_for_async(condition, timeout)

    finally:
        client.remove_event_handler(on_message, events.NewMessage(incoming=True))

    return messages


async def helper_test_transcription_for_file(
    client: TelegramClient, test_file: _TestFile, tmp_path: Path, timeout=30
):
    """
    Test helper. Tests whether transcription is completed correctly (by comparing txt and srt outputs) for a file.

    Also checks we are not sending edit_message more than 1/s.
    """
    with test_file.path.open("rb") as f:
        await client.send_file(
            BOT_USERNAME, file=f, voice_note=True
        )  # TODO it's not actually sent as a voice note, why?
    
    edit_message_count = 0
    start = time.time()

    async def on_edit_message(message: Message):
        nonlocal edit_message_count
        edit_message_count += 1
    
    try:
        client.add_event_handler(on_edit_message, events.MessageEdited(incoming=True))

        # Wait until transcription is complete (3 messages expected)
        messages = await wait_for_new_messages(client, 3, timeout)

        # Download messages
        for msg in messages[1:]:
            assert msg.file is not None
            assert msg.file.name is not None
            await msg.download_media(file=Path(tmp_path) / msg.file.name)

        # txt and srt files expected
        txt_path = tmp_path / f"'{test_file.path.name}'.txt"
        srt_path = tmp_path / f"'{test_file.path.name}'.srt"
        assert txt_path.exists()
        assert srt_path.exists()

        # Check contents
        assert test_file.compare_txt(txt_path.read_text())
        assert test_file.compare_srt(srt_path.read_text())

        seconds = int(time.time() - start)
        assert edit_message_count < seconds

    finally:
        client.remove_event_handler(on_edit_message)