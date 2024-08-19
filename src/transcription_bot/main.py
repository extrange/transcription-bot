"""Setup client and start the bot proper."""

from typing import NoReturn

import uvloop
from telethon import TelegramClient

from .handlers.register import register_handlers
from .settings import Settings
from .utils.logger import setup_logging


async def main() -> NoReturn:
    """Start the bot."""
    setup_logging()
    client = TelegramClient(
        Settings.SESSION_FILE,
        Settings.API_ID,
        Settings.API_HASH.get_secret_value(),
    )

    register_handlers(client)

    await client.start()  # pyright:  ignore[reportGeneralTypeIssues]
    await client.run_until_disconnected()  # pyright:  ignore[reportGeneralTypeIssues]


if __name__ == "__main__":
    uvloop.run(main())
