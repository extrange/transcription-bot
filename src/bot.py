import asyncio
import html
import logging
import time
from asyncio.subprocess import Process
from datetime import datetime
from zoneinfo import ZoneInfo

from humanize import naturalsize
from pyrogram import Client, enums, filters
from pyrogram.types import Message
from typing import Union

from utils import format_hhmmss

MY_CHAT_ID = 427380463
TZ = ZoneInfo("Asia/Singapore")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

# Authorization has already been done and saved in my_account.session
# Authorized for bot @nicktranscriptionbot

app = Client("my_account")

welcome_message = """Send me any audio file or voice message, and I will transcribe the audio from it for you. Transcribe time is approx 1min per minute of audio."""

lock = asyncio.Lock()


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


@app.on_message(filters.text)
async def handle_non_audio(client, message: Message):
    await message.reply_text(welcome_message)


@app.on_message(filters.audio | filters.voice)
async def handle_audio(client, message: Message):
    print(message.chat.id)
    if message.audio:
        file_name = f"'{message.audio.file_name}'"
        download_file_name = message.audio.file_name
        duration = format_hhmmss(message.audio.duration)
        file_size = naturalsize(message.audio.file_size)
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

        # Whisper doesn't print output without -nt
        command = f"ffmpeg -hide_banner -i '{path}' -ac 1 -ar 16000 -c:a pcm_s16le '{path}.wav' && /whisper.cpp/main -otxt -nt -m /whisper.cpp/models/ggml-large.bin '{path}.wav' && rm '{path}.wav'"

        # Convert to .wav with ffmpeg and transcribe with whisper
        subproc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )

        # Log output and update user of progress
        prefix = f"{prefix}\n\nTranscribing..."

        subproc.kill()

        start = time.time()
        output = []

        async def collect_stdout(p: Process):
            if p.stdout:
                while raw := await p.stdout.read(
                    10
                ):  # Can't use .readline() because -nt doesn't output newlines
                    line = raw.decode("utf8")
                    logger.info(line)
                    output.append(line)

        reply = await reply.edit_text(prefix)

        collect_stdout_task = asyncio.create_task(collect_stdout(subproc))

        # Send user live output
        while not collect_stdout_task.done():
            output_lines = "".join(output[-300:])[-300:]
            await reply.edit_text(
                f"{prefix} ({round(time.time()-start)}s)\n\n<pre>{html.escape(output_lines)}</pre>",
                parse_mode=enums.ParseMode.HTML,
            )
            await asyncio.sleep(1)

        # Wait for completion
        exit_code = await subproc.wait()
        time_taken = round(time.time() - start)

        if exit_code == 0:
            await reply.edit_text(f"{prefix}done ({time_taken}s).")

            # Send text file with transcription to user
            await message.reply_document(f"{path}.wav.txt", quote=True)
            await notify_me(message, path, duration, f"{path}.wav.txt")

        else:
            await reply.edit_text(
                f"{prefix}failed ({time_taken}s). Exit status: {exit_code}"
            )
            await notify_me(message, path, duration)


app.run()
