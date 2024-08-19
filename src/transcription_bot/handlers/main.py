import asyncio
import logging
import tempfile
import time
import traceback
from pathlib import Path
from typing import cast

import ffmpeg
import pysubs2
from humanize import naturalsize
from telethon import TelegramClient, errors
from telethon.custom import Button, Message
from telethon.events import StopPropagation
from telethon.types import User

from transcription_bot.settings import Settings

from .utils import format_hhmmss, throttle

_logger = logging.getLogger(__name__)

# Limit to one transcribing task at a time
_lock = asyncio.Lock()


def _is_other_user(message: Message) -> bool:
    return (
        cast(User, message.sender).username != Settings.MY_USERNAME.get_secret_value()
    )


async def download_file(): ...


async def main_handler(message: Message) -> None:
    """Handle all incoming messages, including /start and audio/video files."""
    if not (
        message.audio or message.video or message.voice or message.document
    ):  # document required for webm support
        await message.reply(
            "Send me any audio/video file or voice message, and I will transcribe the audio from it for you. Transcribe time is approx 3x realtime, excluding silences.",
        )
        raise StopPropagation

    sender = None

    try:
        client = cast(TelegramClient, message.client)

        if not (message.file and message.file.size):
            raise ValueError("Failed to parse file!")

        # file name in notification with quotes added
        file_name = f"'{message.file.name}'" if message.file.name else "voice message"
        file_size = naturalsize(value=message.file.size)

        prefix = f"Downloading {file_name}, ({file_size})..."
        reply = cast(Message, await message.reply(prefix, silent=True))

        @throttle(delay=3)
        async def update_dl_progress(received_bytes, total):
            """Update telegram with download progress"""
            new_text = f"{prefix}\n{naturalsize(received_bytes)}/{naturalsize(total)} ({float(received_bytes)/total*100:.1f}%)"
            if reply.text == new_text:
                return
            try:
                await reply.edit(new_text)
            except errors.FloodWaitError as e:
                _logger.error(e)

        # Download audio file
        with tempfile.TemporaryDirectory() as temp_dir:
            dl_path = await message.download_media(
                file=Path(temp_dir) / file_name, progress_callback=update_dl_progress
            )
            if dl_path is None:
                raise Exception("Failed to download file!")

            # Check duration
            duration_s = message.file.duration or float(
                ffmpeg.probe(dl_path)["format"]["duration"]
            )
            duration = format_hhmmss(duration_s)

            prefix = f"Downloaded {file_name} ({duration}, {file_size})."
            sender = message.sender
            sender_name = sender.first_name if sender else "Unknown sender"
            await reply.edit(f"{prefix} Preparing for transcription...")

            # Log file received
            log_msg = f"Received file from '{sender_name}': {prefix}"
            _logger.info(log_msg)
            if _is_other_user(message):
                await client.send_message(
                    Settings.MY_USERNAME.get_secret_value(),
                    log_msg,
                    file=Path(dl_path).open("rb"),
                    silent=True,
                )

            if _lock.locked():
                prefix = f"{prefix}\n\nWaiting in queue..."
                await reply.edit(prefix)

            async with _lock:
                _cancelled_status[message.chat_id] = False

                @throttle
                async def update_transcription_progress(text: str):
                    try:
                        await reply.edit(
                            text, buttons=[Button.inline("cancel")], parse_mode="html"
                        )
                    except errors.FloodWaitError as e:
                        _logger.error(e)

                # Update user of progress
                prefix = f"{prefix}\n\nTranscribing..."
                await reply.edit(
                    f"{prefix}detecting silence... (may take a while)",
                    buttons=[Button.inline("cancel")],
                    parse_mode="html",
                )

                # Start transcribing with faster-whisper
                # Use VAD for speedups
                # Beam size 1 seems to improve performance, compared to default of 5
                segments = model.transcribe(
                    dl_path, beam_size=1, language="en", vad_filter=True
                )[0]

                loop = asyncio.get_running_loop()

                start = time.time()
                results = []

            if _cancelled_status[message.chat_id]:
                await reply.edit(f"{prefix}cancelled.")
                log_msg = f"{sender_name} cancelled transcription."
                _logger.info(log_msg)

                if _is_other_user(message):
                    await client.send_message(
                        Settings.MY_USERNAME.get_secret_value(), log_msg, silent=True
                    )
            else:
                time_taken = round(time.time() - start)

                # Save to txt
                txt_file = Path(temp_dir) / f"{file_name}.txt"
                with txt_file.open("w") as f:
                    f.write("".join([s["text"] for s in results]))

                srt_file = Path(temp_dir) / f"{file_name}.srt"
                with srt_file.open("w") as f:
                    pysubs2.load_from_whisper(results).save(str(srt_file))

                reply_txt = f"{prefix}done in {format_hhmmss(time_taken)}."
                await reply.edit(reply_txt)

                # Send text file with transcription to user
                await message.reply(file=txt_file.open("rb"))
                await message.reply(file=srt_file.open("rb"))

                # Notify me
                log_msg = f"Completed transcription for {sender_name}: {reply_txt}"
                _logger.info(log_msg)
                if _is_other_user(message):
                    await client.send_message(
                        Settings.MY_USERNAME.get_secret_value(),
                        log_msg,
                        file=txt_file.open("rb"),
                        silent=True,
                    )

    except Exception as e:
        log_msg = f"Received error from {sender.first_name if sender else 'Unknown sender'}:\n\n<pre>{traceback.format_exc()}</pre>"
        _logger.error(log_msg)
        if _is_other_user(message):
            await client.send_message(
                Settings.MY_USERNAME.get_secret_value(), log_msg, parse_mode="html"
            )

        await message.reply(f"Encountered error:\n\n<pre>{e}</pre>", parse_mode="html")
