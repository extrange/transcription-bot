import logging
import tempfile
import time
from functools import partial
from pathlib import Path
from typing import cast

from python_utils import format_hhmmss
from telethon import TelegramClient
from telethon.custom import Message
from telethon.events import StopPropagation

from transcription_bot.file_api.minio_api import FileApi
from transcription_bot.file_api.policy import Policy
from transcription_bot.handlers.types import TranscriptionFailedError
from transcription_bot.handlers.utils import (
    is_other_user,
    notify_error,
)
from transcription_bot.settings import Settings
from transcription_bot.transcribe import BaseTranscriber, ReplicateTranscriber
from transcription_bot.types import ModelParamsWithoutUrl

from .download import DownloadHandler
from .utils import get_sender_name, on_update

_logger = logging.getLogger(__name__)


async def _log_progress(reply_msg: Message, progress: str) -> None:
    progress_msg = f"Processing...\n<pre>{progress}</pre>"
    await on_update(reply_msg, progress_msg)


async def _get_transcript(
    transcriber: BaseTranscriber,
    reply_msg: Message,
    url: str,
    save_dir: Path,
) -> Path:
    """
    Transcribe an audio file that was uploaded to file storage and save the result as a txt file.

    `save_dir`: Temporary directory which to store the text file.

    Returns the path to the file.
    """
    result, status = await transcriber.send_job(
        url,
        log_cb=partial(_log_progress, reply_msg=reply_msg),
    )
    if not result:
        msg = f"{status=}"
        raise TranscriptionFailedError(msg)

    txt_file = Path(save_dir) / f"{int(time.time())}.txt"
    with txt_file.open("w") as f:
        f.write(result)
    return txt_file


async def main_handler(message: Message) -> None:
    """Handle all incoming messages, including /start and audio/video files."""
    _logger.debug("test")
    if not DownloadHandler.should_handle_message(message):
        reply_msg = cast(
            Message,
            await message.reply(
                "Send me any audio/video file or voice message, and I will transcribe the audio from it for you. Transcribe time is approx 3x realtime, excluding silences.",
                silent=True,
            ),
        )
        raise StopPropagation

    reply_msg = cast(Message, await message.reply("Processing...", silent=True))

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

    try:
        handler = DownloadHandler(message, reply_msg, api)
        url = await handler.download()

    except Exception as e:
        await notify_error(message, "Encountered error:", e)
        raise StopPropagation from e

    with tempfile.TemporaryDirectory() as temp_dir:
        start = time.time()
        try:
            txt_file = await _get_transcript(
                transcriber,
                reply_msg,
                url,
                Path(temp_dir),
            )
        except Exception as e:
            await notify_error(message, "Transcription failed", e)
            raise StopPropagation from e

        done_txt = f"Transcription done in {format_hhmmss(time.time() - start)}."
        await reply_msg.edit(done_txt)
        await message.reply(file=txt_file.open("rb"))

        # Notify me
        log_msg = f"Completed transcription for {get_sender_name(message)}: {done_txt}"
        _logger.info(log_msg)
        if is_other_user(message):
            await cast(TelegramClient, message.client).send_message(
                Settings.MY_USERNAME.get_secret_value(),
                log_msg,
                file=txt_file.open("rb"),
                silent=True,
            )
