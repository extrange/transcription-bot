import logging

from telethon import TelegramClient, events, functions, types

from .main import main_handler

logger = logging.getLogger(__name__)


def register_handlers(client: TelegramClient):
    """
    Register Telethon handlers.

    Registered handlers will be called in order, so add the most specific ones first.

    Raise a StopPropagation if no further handlers should handle the message.
    """
    client.add_event_handler(
        main_handler,
        events.NewMessage(
            incoming=True,
        ),
    )
    logger.info("Registered handlers successfully.")
