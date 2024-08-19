"""Setup client and start the bot proper."""

from pathlib import Path
from typing import NoReturn

import uvloop
from telethon import TelegramClient

from .utils.logger import setup_logging


async def main() -> NoReturn:
    """Start the bot."""
    setup_logging()
    client = TelegramClient(
        str(Path(__file__).parent.parent.parent / "my_account.session"),
        Credentials.API_ID,
        Credentials.API_HASH,
    )

    register_handlers(client)

    await client.start()  # pyright:  ignore[reportGeneralTypeIssues]
    await client.run_until_disconnected()  # pyright:  ignore[reportGeneralTypeIssues]


if __name__ == "__main__":
    uvloop.run(main())
