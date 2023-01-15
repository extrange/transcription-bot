import asyncio
import re
import html
import logging
import shlex
import time
from asyncio.subprocess import Process
from datetime import datetime
from typing import Union
from zoneinfo import ZoneInfo

from dotenv import dotenv_values
from humanize import naturalsize
from pyrogram import enums, filters
from pyrogram.client import Client
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pathlib import Path
from utils import format_hhmmss

MY_CHAT_ID = int(dotenv_values(Path(__file__).parent / '.env')["MY_CHAT_ID"] or "")
TZ = ZoneInfo("Asia/Singapore")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

# Authorization has already been done and saved in my_account.session
# Authorized for bot @nicktranscriptionbot

app = Client("my_account")

welcome_message = """Send me any audio/video file or voice message, and I will transcribe the audio from it for you. Transcribe time is approx 1min per minute of audio."""

lock = asyncio.Lock()

cancelled_status = {}


async def notify_me(
    message: Message,
    audio_file: str,
    duration: str,
    transcript: Union[str, None] = None,
):
    if message.chat.id == MY_CHAT_ID:
        return

    await app.send_audio(
        MY_CHAT_ID,
        audio_file,
        caption=f"Received file {audio_file} ({duration}) from {message.from_user.first_name}.",
    )

    if transcript:
        await app.send_document(MY_CHAT_ID, transcript)
    else:
        await app.send_message(MY_CHAT_ID, "Encountered error while transcribing.")


@app.on_callback_query()
async def handle_cancel(client, callback_query: CallbackQuery):
    if callback_query.data == "cancel":
        message = callback_query.message
        cancelled_status[message.id] = True
        await message.edit_reply_markup()


@app.on_message(filters.text)
async def handle_non_audio(client, message: Message):
    await message.reply_text(welcome_message)


@app.on_message(filters.audio | filters.voice | filters.video | filters.document)
async def handle_audio(client, message: Message):
    if message.document:
        file_name = f"'{message.document.file_name}'" # file name in notification with quotes added
        download_file_name = message.document.file_name
        duration = 'unknown'
        file_size = naturalsize(message.document.file_size)
    elif message.audio or message.video:
        audio_video = message.audio if message.audio else message.video
        file_name = f"'{audio_video.file_name}'"
        download_file_name = audio_video.file_name
        duration = format_hhmmss(audio_video.duration)
        file_size = naturalsize(audio_video.file_size)
    else:
        file_name = f"voice message"
        download_file_name = "voice.ogg"
        duration = format_hhmmss(message.voice.duration)
        file_size = naturalsize(message.voice.file_size)

    prefix = f"Downloading {file_name}..."
    reply = await message.reply_text(prefix, quote=True, disable_notification=True)

    async def print_progress(current, total):
        new_text = f"{prefix}\n{naturalsize(current)}/{naturalsize(total)} ({float(current)/total*100:.1f}%)"
        if reply.text == new_text:
            return
        await reply.edit_text(new_text)

    # Download audio file
    path = await message.download(
        f'{message.from_user.first_name}_{datetime.now(TZ).strftime("%Y%m%d-%H%M%S")}_{download_file_name}',
        progress=print_progress,
    )

    logger.info(
        f"{message.from_user.first_name}: Downloaded {file_name} ({duration}, {file_size}) to {path}"
    )

    prefix = f"Downloaded {file_name} ({duration}, {file_size})."
    await reply.edit_text(f"{prefix}")

    if lock.locked():
        prefix = f"{prefix}\n\nWaiting in queue..."
        await reply.edit_text(prefix)

    async with lock:

        cancelled_status[reply.id] = False
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", "cancel")]])

        # Convert to .wav with ffmpeg and transcribe with whisper
        commands = [
            f"ffmpeg -hide_banner -i '{path}' -ac 1 -ar 16000 -c:a pcm_s16le '{path}.wav'",
            # Whisper doesn't print output without -nt
            f"/whisper.cpp/main -otxt -osrt -nt -m /whisper.cpp/models/ggml-large.bin '{path}.wav'",
            f"rm '{path}.wav'",
        ]

        # Log output and update user of progress
        prefix = f"{prefix}\n\nTranscribing..."
        reply = await reply.edit_text(prefix, reply_markup=markup)

        start = time.time()
        output = []

        async def collect_stdout(p: Process):
            if p.stdout:
                while raw := await p.stdout.read(
                    10
                ):  # Can't use .readline() because -nt doesn't output newlines
                    line = raw.decode("utf8")
                    output.append(line)

        async def run_commands():
            proc = None
            return_code = None
            try:
                for command in commands:
                    proc = await asyncio.subprocess.create_subprocess_exec(
                        *shlex.split(command),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                    )
                    task = asyncio.create_task(collect_stdout(proc))
                    return_code = await proc.wait()
            except asyncio.CancelledError:
                logger.info(
                    f"User {message.from_user.first_name} cancelled task for {path}."
                )
                if proc:
                    proc.kill()
            finally:
                return return_code

        run_commands_task = asyncio.create_task(run_commands())

        # Send user live output
        while not run_commands_task.done():
            output_lines = "".join(output[-300:])[-300:]
            await reply.edit_text(
                f"{prefix} ({format_hhmmss(round(time.time()-start))})\n\n<pre>{html.escape(output_lines)}</pre>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=markup,
            )
            if cancelled_status[reply.id]:
                run_commands_task.cancel()

            await asyncio.sleep(1)

        # Flush to log
        [logger.info(line) for line in "".join(output).split("\n")]

        # Release lock

    time_taken = round(time.time() - start)
    exit_code = run_commands_task.result()

    if exit_code == 0:
        await reply.edit_text(f"{prefix}done ({format_hhmmss(time_taken)}).")

        # Send text file with transcription to user
        output_txt = f"{path}.wav.txt"
        with open(output_txt) as f:
            text = f.read()
        text = re.sub('\n', '', text).strip()
        with open(output_txt, 'w') as f:
            f.write(text)
        await message.reply_document(f"{path}.wav.txt", quote=True)
        await message.reply_document(f"{path}.wav.srt", quote=True)
        await notify_me(message, path, duration, f"{path}.wav.txt")

    else:
        await reply.edit_text(
            f"{prefix}failed ({format_hhmmss(time_taken)}). Exit status: {exit_code}"
        )
        await notify_me(message, path, duration)


app.run()
