import asyncio
import html
import logging
import tempfile
import time
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

import pysubs2
from dotenv import dotenv_values
from faster_whisper import WhisperModel
from humanize import naturalsize
import ffmpeg
from pyrogram import enums, filters
from pyrogram.client import Client
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from utils import format_hhmmss

MY_CHAT_ID = int(dotenv_values(Path(__file__).parent / ".env")["MY_CHAT_ID"] or "")
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

cancelled_status = {}

# Limit to one transcribing task at a time
lock = asyncio.Lock()

# Load model
model = WhisperModel("large-v2", device="cpu", compute_type="int8")


async def is_other_user(message: Message) -> bool:
    return message.chat.id != MY_CHAT_ID


@app.on_callback_query()
async def handle_cancel(client, callback_query: CallbackQuery):
    if callback_query.data == "cancel":
        message = callback_query.message
        cancelled_status[message.id] = True
        await message.edit_reply_markup()
        await message.edit_text(message.text + "\n\nCancelling...")


@app.on_message(filters.text)
async def handle_non_audio(client, message: Message):
    await message.reply_text(welcome_message)


@app.on_message(filters.audio | filters.voice | filters.video | filters.document)
async def handle_audio(client, message: Message):
    try:
        if message.document:
            file_name = f"'{message.document.file_name}'"  # file name in notification with quotes added
            file_size = naturalsize(message.document.file_size)
        elif message.audio or message.video:
            audio_video = message.audio if message.audio else message.video
            file_name = f"'{audio_video.file_name}'"
            file_size = naturalsize(audio_video.file_size)
        else:
            file_name = f"voice message"
            file_size = naturalsize(message.voice.file_size)

        prefix = f"Downloading {file_name}..."
        reply = await message.reply_text(prefix, quote=True, disable_notification=True)

        async def update_dl_progress(current, total):
            """Update telegram with download progress"""
            new_text = f"{prefix}\n{naturalsize(current)}/{naturalsize(total)} ({float(current)/total*100:.1f}%)"
            if reply.text == new_text:
                return
            await reply.edit_text(new_text)

        # Download audio file
        with tempfile.TemporaryDirectory() as temp_dir:
            path = await message.download(
                str(Path(temp_dir) / file_name), progress=update_dl_progress
            )

            duration_s = float(ffmpeg.probe(path)["format"]["duration"])

            prefix = (
                f"Downloaded {file_name} ({format_hhmmss(duration_s)}, {file_size})."
            )
            logger.info(f"{message.from_user.first_name}: {prefix}")
            await reply.edit_text(f"{prefix}")

            # Notify me
            if is_other_user(message):
                await app.send_audio(
                    MY_CHAT_ID,
                    path,
                    caption=f"Received file {file_name} ({format_hhmmss(duration_s)}) from {message.from_user.first_name}.",
                )

            if lock.locked():
                prefix = f"{prefix}\n\nWaiting in queue..."
                await reply.edit_text(prefix)

            async with lock:
                cancelled_status[reply.id] = False
                markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Cancel", "cancel")]]
                )

                async def update_transcription_progress(text: str):
                    await reply.edit_text(
                        text,
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=markup,
                    )

                # Log output and update user of progress
                prefix = f"{prefix}\n\nTranscribing..."
                reply = await reply.edit_text(
                    f"{prefix}detecting silences... (may take a while)",
                    reply_markup=markup,
                )

                # Start transcribing with faster-whisper
                # Use VAD for speedups
                # Beam size 1 seems to improve performance, compared to default of 5
                segments = model.transcribe(
                    path, beam_size=1, language="en", vad_filter=True
                )[0]

                loop = asyncio.get_running_loop()

                start = time.time()
                results = []

                def process():
                    for s in segments:
                        if cancelled_status[reply.id]:
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

            time_taken = round(time.time() - start)

            # Save to txt
            txt_file = Path(temp_dir) / f"{file_name}.txt"
            with txt_file.open("w") as f:
                f.write("".join([s["text"] for s in results]))

            srt_file = Path(temp_dir) / f"{file_name}.srt"
            with srt_file.open("w") as f:
                pysubs2.load_from_whisper(results).save(str(srt_file))

            if cancelled_status[reply.id]:
                await reply.edit_text(f"{prefix}cancelled.")
            else:
                await reply.edit_text(f"{prefix}done in {format_hhmmss(time_taken)}.")

                # Send text file with transcription to user
                await message.reply_document(str(txt_file), quote=True)
                await message.reply_document(str(srt_file), quote=True)

                # Notify me
                if is_other_user(message):
                    await app.send_document(MY_CHAT_ID, str(txt_file))

    except Exception as e:
        await message.reply(
            f"Encountered error:\n\n<pre>{e}</pre>", parse_mode=enums.ParseMode.HTML
        )

        if is_other_user(message):
            await app.send_message(
                MY_CHAT_ID,
                f"Received error from {message.from_user.first_name}:\n"
                f"\n"
                f"<pre>{traceback.format_exc()}</pre>",
                parse_mode=enums.ParseMode.HTML,
            )


app.run()
