import logging
import tempfile
from collections.abc import Callable, Coroutine
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from humanize import naturalsize
from python_utils import athrottle, format_hhmmss
from telethon import TelegramClient
from telethon.custom import Message
from telethon.tl.custom.file import File

from transcription_bot.file_api.base_api import BaseApi
from transcription_bot.handlers.types import DownloadFailedError
from transcription_bot.handlers.utils import (
    ffprobe_get_duration_s,
    is_other_user,
)
from transcription_bot.settings import Settings

from .utils import get_sender_name, on_update

_logger = logging.getLogger(__name__)


class DownloadHandler:
    """A method class which performs downloads from messages, uploads to Minio and then updates the user."""

    def __init__(self, message: Message, reply_msg: Message, api: BaseApi) -> None:
        """
        Create a new handler for transcription requests.

        `message`: The message to process.
        `temp_dir`: A tempo
        """
        self.message = message
        self.reply_msg = reply_msg
        self.api = api

    @staticmethod
    def should_handle_message(message: Message) -> bool:
        """Check if  message has media attached."""
        # webm files are considered documents
        return bool(
            message.audio or message.video or message.voice or message.document
        ) or bool(message.file)

    def _get_file_size(self, file: File) -> str:
        return naturalsize(value=file.size) if file.size else "unknown size"

    def _get_file_name(self, file: File) -> str:
        return f"'{file.name}'" if file.name else "voice message"

    async def _upload_file(self, path: Path) -> str:
        """
        Upload file using a BaseApi class.

        Suffixes the current timestamp to the filename, for the destination filename.
        """
        now = datetime.now(tz=ZoneInfo(Settings.TZ)).isoformat().replace(":", "-")
        destination_name = f"{path.stem}_{now}{path.suffix or ""}"
        orig_reply_txt = str(self.reply_msg.text)
        await self.reply_msg.edit(orig_reply_txt + "\nUploading...")
        url = self.api.upload_file(path, destination_name)
        await self.reply_msg.edit(orig_reply_txt + "\nUpload complete.")
        return url

    async def download(self) -> str:
        """
        Start downloading content from a message.

        Keeps the user informed of progress.

        Raises NoMediaFileError if there was no media in the message, or DownloadFailedError if download was unsuccessful.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dl_path = await self._download_file(Path(temp_dir))
            return await self._upload_file(dl_path)

    def _on_download_update(
        self,
        message: Message,
        prefix: str | None = None,
        delay: float = 3,
    ) -> Callable[[int, int], Coroutine[Any, Any, None]]:
        """
        Edits a telegram message with the download progress.

        `message`: The message to update.
        `prefix`: Optional prefix included before the download progress.
        `delay`: Max frequency of updates (throttled)

        For use with message.download_media as progress_callback.
        """

        @athrottle(delay=delay)
        async def _handler(received_bytes: int, total: int) -> None:
            text = f"{prefix or ""}\n{naturalsize(received_bytes)}/{naturalsize(total)} ({received_bytes/total*100:.1f}%)"
            await on_update(message, text)

        return _handler

    async def _download_file(self, dl_dir: Path) -> Path:
        """Download file from the message, keeping the user updated. Also notifies me."""
        message = self.message

        file = cast(File, message.file)

        file_size = self._get_file_size(file)
        file_name = self._get_file_name(file)

        # Inform user we are starting download
        prefix = f"Downloading {file_name}, ({file_size})..."
        await self.reply_msg.edit(prefix)

        # Download file
        dl_path_str = cast(
            str | None,
            await message.download_media(
                file=dl_dir / file_name,
                progress_callback=self._on_download_update(self.reply_msg, prefix),
            ),
        )

        if dl_path_str is None:
            raise DownloadFailedError

        dl_path = Path(dl_path_str)

        duration_s = file.duration or ffprobe_get_duration_s(dl_path)
        duration = format_hhmmss(duration_s)

        prefix = f"Downloaded {file_name} ({duration}, {file_size})."

        await self.reply_msg.edit(f"{prefix} Preparing for transcription...")

        sender_name = get_sender_name(message)

        log_msg = f"Received file from '{sender_name}': {prefix}"
        _logger.info(log_msg)
        if is_other_user(message):
            await cast(TelegramClient, message.client).send_message(
                Settings.MY_USERNAME.get_secret_value(),
                log_msg,
                file=dl_path.open("rb"),  # noqa: ASYNC230
                silent=True,
            )

        return dl_path
