import logging

from telethon import events
from telethon.events import StopPropagation

from transcription_bot.handlers.utils import notify_error
from transcription_bot.transcribers.replicate import ReplicateTranscriber

from .utils import get_sender_name

_logger = logging.getLogger(__name__)


async def handle_cancel(event: events.CallbackQuery.Event) -> None:
    """Handle cancel callbacks for predictions."""
    data: bytes = event.data
    message = await event.get_message()

    if not message:
        _logger.error("No message attached to callback")
        raise StopPropagation
    sender = get_sender_name(message)

    _logger.info("Received callback data from %s: %s", sender, data)

    try:
        await ReplicateTranscriber.cancel(data.decode())
    except Exception as e:  # noqa: BLE001
        await notify_error(
            message,
            f"Failed to cancel transcription for {sender} (received {data=})",
            e,
        )

    await message.edit("Cancelled transcription.", buttons=None)
