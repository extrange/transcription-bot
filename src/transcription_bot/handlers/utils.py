import asyncio
import functools
import logging
import time
import traceback
from collections.abc import Callable, Coroutine
from datetime import timedelta
from pathlib import Path
from typing import Any, cast, overload

import ffmpeg
from telethon import TelegramClient, errors
from telethon.custom import Message
from telethon.types import User

from transcription_bot.settings import Settings

_logger = logging.getLogger(__name__)


def format_hhmmss(s: float) -> str:
    """Format seconds into HH:MM:SS format."""
    delta = timedelta(seconds=s)
    hours = delta.days * 24 + delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"


type _Coro[T] = Coroutine[Any, Any, T]
type _WrappedDeco[**P, T] = Callable[
    [Callable[P, _Coro[T]]],
    Callable[P, _Coro[T | None]],
]


@overload
def athrottle[**P, R](*, delay: float = 1) -> _WrappedDeco[P, R]: ...


@overload
def athrottle[**P, T](
    _func: Callable[P, _Coro[T]],
    *,
    delay: float = 1,
) -> Callable[P, _Coro[T | None]]: ...


def athrottle[**P, T](
    _func: Callable[P, _Coro[T]] | None = None,
    *,
    delay: float = 1,
) -> Callable[P, _Coro[T | None]] | _WrappedDeco[P, T]:
    """
    Decorate an async function with throttle.

    Returns `None` if called within window.
    """

    def decorate(
        func: Callable[P, _Coro[T]],
    ) -> Callable[P, _Coro[T | None]]:
        last_called: float | None = None
        lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapped_async(*args: P.args, **kwargs: P.kwargs) -> T | None:
            # The lock is necessary to ensure that tasks created at the same time don't simultaneously modify last_called
            async with lock:
                nonlocal last_called
                now = time.time()
                result = None
                if not last_called or now - last_called > delay:
                    result = await func(*args, **kwargs)
                    last_called = now
            return result

        return wrapped_async

    if _func:
        # Decorator called without arguments: _func is passed
        # We apply and return the decorated function (with default values)
        return decorate(_func)
    # Decorator called with arguments: _func will be None
    # We return the decorator (as a closure), which will then be applied to the function
    return decorate


async def on_update(message: Message, text: str) -> None:
    """Update a telegram message with the text. Use as a callback."""
    # Don't update the message if it is identical or Telegram will throw errors
    if message.text == text:
        return
    try:
        await message.edit(text)
    except errors.FloodWaitError:
        _logger.exception("FloodWaitError: not sending message '%s", text)


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

    _logger.error(err_msg)

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
