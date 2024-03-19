"""
Setup client and start the bot proper.
"""

import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

from pathlib import Path

import uvloop
from transcriptionbot.bot import credentials, register_handlers
from telethon import TelegramClient

async def main():
    client = TelegramClient(
        str(Path(__file__).parent.parent.parent / "my_account.session"),
        credentials.API_ID,
        credentials.API_HASH,
    )

    register_handlers(client)

    await client.start()  # type: ignore
    await client.run_until_disconnected()  # type: ignore


if __name__ == "__main__":
    uvloop.run(main())
