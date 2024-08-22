import logging
import traceback
from pathlib import Path
from typing import cast

import ffmpeg
from telethon import TelegramClient, errors
from telethon.custom import Message
from telethon.types import User

from transcription_bot.settings import Settings

_logger = logging.getLogger(__name__)


async def on_update(message: Message, text: str, parse_mode: str = "html") -> None:
    """Update a telegram message with the text. Use as a callback."""
    # Don't update the message if it is identical or Telegram will throw errors
    try:
        await message.edit(text, parse_mode=parse_mode)
    except errors.FloodWaitError:
        _logger.exception("FloodWaitError: not sending message '%s", text)
    except errors.MessageNotModifiedError:
        # How to get original message text?
        pass


def is_other_user(message: Message) -> bool:
    """Return whether a message is sent from another user other than myself."""
    return (
        cast(User, message.sender).username != Settings.MY_USERNAME.get_secret_value()
    )


async def notify_error(
    message: Message,
    err_msg: str,
    exc: Exception | None = None,
) -> None:
    """
    Notify a user of an error, as well as myself. Also logs the error.

    `message`: The initial message sent by the user, which triggered the handler.
    `err_msg`: Error message to the user
    `exc`: Related exception, if any.
    """
    client = cast(TelegramClient, message.client)
    _err_msg = f"{err_msg}:\n<pre>{"".join(traceback.format_exception(exc, limit=5)) if exc else "No additional details available"}</pre>"

    sender = cast(User, await message.get_sender())

    _logger.exception(err_msg)

    if is_other_user(message):
        # Notify me
        await client.send_message(
            Settings.MY_USERNAME.get_secret_value(),
            f"Received error from {sender.first_name}:\n\n{_err_msg}",
            parse_mode="html",
        )

    await message.reply(f"Encountered error:\n\n{_err_msg}", parse_mode="html")


def get_sender_name(message: Message) -> str:
    """Return a message's sender's first_name."""
    sender = message.sender
    return sender.first_name if sender else "Unknown sender"


def ffprobe_get_duration_s(path: Path) -> float:
    """Get duration of a media file."""
    return float(ffmpeg.probe(path)["format"]["duration"])


async def notify_me(message: Message, text: str, file: Path | None) -> None:
    """
    Notify me with a message, optionally including a file.

    Also logs the message.

    Includes the sender's name.
    """
    if not is_other_user(message):
        return

    sender = get_sender_name(message)
    log_msg = f"Notification from {sender}:\n{text}"
    _logger.info(log_msg)

    await cast(TelegramClient, message.client).send_message(
        Settings.MY_USERNAME.get_secret_value(),
        log_msg,
        file=file.open("rb") if file else None,  # pyright: ignore[reportArgumentType]
        silent=True,
    )
