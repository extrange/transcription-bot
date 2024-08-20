import logging
import tempfile
import time
from functools import partial
from pathlib import Path
from typing import cast

from python_utils import format_hhmmss
from telethon import Button
from telethon.custom import Message
from telethon.events import StopPropagation

from transcription_bot.file_api.minio_api import FileApi
from transcription_bot.file_api.policy import Policy
from transcription_bot.handlers.summary import generate_summary
from transcription_bot.handlers.types import TranscriptionFailedError
from transcription_bot.handlers.utils import (
    notify_error,
)
from transcription_bot.settings import Settings
from transcription_bot.transcribers.base import BaseTranscriber
from transcription_bot.transcribers.replicate import ReplicateTranscriber
from transcription_bot.types import ModelParamsWithoutUrl

from .download import DownloadHandler
from .utils import notify_me, on_update

_logger = logging.getLogger(__name__)


async def _log_progress(
    progress: str, reply_msg: Message, limit_lines: int = 3
) -> None:
    text = progress.splitlines()[-limit_lines:]
    progress_msg = f"Processing...\n<pre>{text}</pre>"
    await on_update(reply_msg, progress_msg)


async def _get_transcript(
    transcriber: BaseTranscriber,
    reply_msg: Message,
    url: str,
    save_dir: Path,
) -> tuple[Path, str]:
    """
    Transcribe an audio file that was uploaded to file storage and save the result as a txt file.

    `save_dir`: Temporary directory which to store the text file.

    Returns tuple of (path to the file, transcript).
    """
    pred_id = await transcriber.send_job(
        url,
        log_cb=partial(_log_progress, reply_msg=reply_msg),
    )
    await reply_msg.reply("Transcribing...", buttons=[Button.inline("Cancel", pred_id)])
    result, status = await transcriber.get_result()

    if not result:
        if status == "canceled":
            await reply_msg.edit("Cancelled transcription.")
            raise StopPropagation
        msg = f"{status=}"
        raise TranscriptionFailedError(msg)

    txt_file = Path(save_dir) / f"{int(time.time())}.txt"
    with txt_file.open("w") as f:
        f.write(result)
    return txt_file, result


def _prepare_api_and_transcriber() -> tuple[FileApi, BaseTranscriber]:
    api = FileApi(
        host=Settings.MINIO_HOST,
        access_key=Settings.MINIO_ACCESS_KEY.get_secret_value(),
        bucket_name=Settings.MINIO_BUCKET,
        secret_key=Settings.MINIO_SECRET_KEY.get_secret_value(),
        default_policy=Policy.public_read_only(),
    )
    transcriber: BaseTranscriber = ReplicateTranscriber(
        Settings.MODEL_VERSION,
        ModelParamsWithoutUrl(),
    )
    return api, transcriber


async def _download(message: Message, reply_msg: Message, api: FileApi) -> str:
    """
    Download the file attached to the message.

    Returns the
    """
    try:
        handler = DownloadHandler(message, reply_msg, api)
        url = await handler.download()

    except Exception as e:
        await notify_error(message, "Encountered error:", e)
        raise StopPropagation from e
    return url


async def main_handler(message: Message) -> None:
    """Handle all incoming messages, including /start and audio/video files."""
    _logger.debug("test")
    if not DownloadHandler.should_handle_message(message):
        reply_msg = cast(
            Message,
            await message.reply(
                "Send me any audio/video file or voice message, and I will transcribe the audio from it for you. Transcribe time is approx 10x realtime.",
                silent=True,
            ),
        )
        raise StopPropagation

    reply_msg = cast(Message, await message.reply("Processing...", silent=True))

    api, transcriber = _prepare_api_and_transcriber()

    url = await _download(message, reply_msg, api)

    with tempfile.TemporaryDirectory() as temp_dir:
        start = time.time()
        try:
            txt_file, transcript = await _get_transcript(
                transcriber,
                reply_msg,
                url,
                Path(temp_dir),
            )
        except StopPropagation:
            raise
        except Exception as e:
            await notify_error(message, "Transcription failed", e)
            raise StopPropagation from e

        done_txt = f"Transcription done in {format_hhmmss(time.time() - start)}."
        await reply_msg.edit(done_txt)
        await message.reply(file=txt_file.open("rb"))

        # Notify me
        log_msg = f"Completed transcription: {done_txt}"
        await notify_me(message, log_msg, txt_file)

        # Generate transcript
        minutes_msg = cast(Message, await message.reply("Generating minutes..."))
        minutes = await generate_summary(transcript)
        if not minutes:
            await notify_error(message, "Failed to generate minutes!")
            raise StopPropagation

        with Path(temp_dir) / f"{int(time.time())}_minutes.txt" as f:
            f.write_text(minutes)
            await minutes_msg.edit("Minutes generated.")
            await message.reply(file=f)
            summary_done_msg = "Completed summary."
            await notify_me(message, summary_done_msg, f)
