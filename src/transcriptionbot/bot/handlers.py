import asyncio
import html
import logging
import tempfile
import time
import traceback
from pathlib import Path
from typing import cast

import ffmpeg
import pysubs2
from humanize import naturalsize
from telethon import TelegramClient, events
from telethon.custom import Button, Message
from telethon.types import User

from .credentials import Credentials
from .model import model
from .utils import format_hhmmss, throttle

_logger = logging.getLogger(__name__)

_welcome_message = """Send me any audio/video file or voice message, and I will transcribe the audio from it for you. Transcribe time is approx 3x realtime, excluding silences."""

# Whether we should cancel the job on the next process tick
_cancelled_status = {}

# Limit to one transcribing task at a time
_lock = asyncio.Lock()


def _is_other_user(message: Message) -> bool:
    return cast(User, message.sender).username != Credentials.MY_USERNAME


def register_handlers(client: TelegramClient):
    client.add_event_handler(_handle_cancel, events.CallbackQuery(data="cancel"))
    client.add_event_handler(_handle_msg, events.NewMessage(incoming=True))


async def _handle_cancel(event: events.CallbackQuery.Event):
    message = cast(Message, await event.get_message())
    _cancelled_status[event.chat_id] = True
    await message.edit(text=cast(str, message.text) + "\n\nCancelling...", buttons=None)
    await event.answer()


async def _handle_msg(message: Message):
    if not (
        message.audio or message.video or message.voice or message.document
    ):  # document required for webm support
        await message.reply(_welcome_message)
        return

    try:
        client = cast(TelegramClient, message.client)

        if not (message.file and message.file.size):
            raise Exception("Failed to parse file!")

        # file name in notification with quotes added
        file_name = f"'{message.file.name}'" if message.file.name else "voice message"
        file_size = naturalsize(message.file.size)

        prefix = f"Downloading {file_name}, ({file_size})..."
        reply = cast(Message, await message.reply(prefix, silent=True))

        @throttle
        async def update_dl_progress(received_bytes, total):
            """Update telegram with download progress"""
            new_text = f"{prefix}\n{naturalsize(received_bytes)}/{naturalsize(total)} ({float(received_bytes)/total*100:.1f}%)"
            if reply.text == new_text:
                return
            await reply.edit(new_text)

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
                    Credentials.MY_USERNAME,
                    log_msg,
                    file=Path(dl_path).open("rb"),
                    silent=True,
                )

            if _lock.locked():
                prefix = f"{prefix}\n\nWaiting in queue..."
                await reply.edit(prefix)

            async with _lock:
                _cancelled_status[message.chat_id] = False

                # TODO throttle this async function
                async def update_transcription_progress(text: str):
                    await reply.edit(
                        text, buttons=[Button.inline("cancel")], parse_mode="html"
                    )

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

                def process():
                    for s in segments:
                        if _cancelled_status[message.chat_id]:
                            break
                        segment_dict = {"start": s.start, "end": s.end, "text": s.text}
                        elapsed_time = time.time() - start
                        frac_done = s.end / duration_s
                        speed = frac_done / elapsed_time
                        est_time_left = (1 - frac_done) / speed
                        update_string = f"{prefix} {format_hhmmss(elapsed_time)}<{format_hhmmss(est_time_left)}\n\n<pre>{html.escape(s.text)}</pre>"
                        results.append(segment_dict)
                        loop.create_task(update_transcription_progress(update_string))

                future = asyncio.get_running_loop().run_in_executor(None, process)

                while not future.done():
                    await asyncio.sleep(1)

            if _cancelled_status[message.chat_id]:
                await reply.edit(f"{prefix}cancelled.")
                log_msg = f"{sender_name} cancelled transcription."
                await client.send_message(Credentials.MY_USERNAME, log_msg, silent=True)
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
                        Credentials.MY_USERNAME,
                        log_msg,
                        file=txt_file.open("rb"),
                        silent=True,
                    )

    except Exception as e:

        log_msg = f"Received error from {sender.first_name if sender else 'Unknown sender'}:\n\n<pre>{traceback.format_exc()}</pre>"
        _logger.error(log_msg)
        if _is_other_user(message):
            await client.send_message(
                Credentials.MY_USERNAME, log_msg, parse_mode="html"
            )

        await message.reply(f"Encountered error:\n\n<pre>{e}</pre>", parse_mode="html")
