import asyncio
import logging
import random
from typing import NamedTuple

import pytest
import pytest_asyncio
import uvloop
from pytest_asyncio import is_async_test
from telethon import TelegramClient, errors, functions
from utils import get_random_string

from transcriptionbot.bot.credentials import Credentials
from transcriptionbot.bot.handlers import register_handlers

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


class ClientTuple(NamedTuple):
    client: TelegramClient
    username: str


class ClientGroup(NamedTuple):
    bot: ClientTuple
    me: ClientTuple
    other: ClientTuple


async def setup_account(username: str):
    """
    Setup a telegram test account with a username.
    Rotates between random DCs and phone numbers.
    See https://core.telegram.org/api/auth#test-accounts
    """

    test_phone_number = random.randint(0, 9999)

    client = TelegramClient(None, Credentials.API_ID, Credentials.API_HASH)  # type: ignore
    client.session.set_dc(2, "149.154.167.40", 80)  # type: ignore

    attempts = 0

    while attempts < 3 and (
        # is_user_authorized() requires client to be connected
        not client.is_connected() or not await client.is_user_authorized()
    ):
        try:
            await client.start(phone=lambda: f"999662{test_phone_number:0>4}", code_callback=lambda: "22222")  # type: ignore
        except errors.rpcerrorlist.PhoneNumberUnoccupiedError:
            # Use another phone number
            logger.info(f"Phone number {test_phone_number} unoccupied, {attempts=}")
            test_phone_number = random.randint(0, 9999)
        attempts += 1

    try:
        # Accounts don't seem to have their username set
        await client(functions.account.UpdateUsernameRequest(username=username))
        logger.info(f"Using {test_phone_number=}, {username=}")
    except Exception as e:
        logger.info(f"Error while setting username: {e}")
        raise e
    return client


@pytest.fixture(scope="function")
async def clients():
    """
    Sets up the client for each test session.
    Also changes the value of MY_USERNAME
    """

    # Generate new usernames
    _clients: list[asyncio.Task[TelegramClient]] = []
    usernames = [get_random_string() for _ in range(3)]

    # Change MY_USERNAME in library to ClientGroup.me
    Credentials.MY_USERNAME = usernames[1]

    async with asyncio.TaskGroup() as tg:
        for i in range(3):
            _clients.append(tg.create_task(setup_account(usernames[i])))

    client_tuple = ClientGroup(
        *[
            ClientTuple(x[0], x[1])
            for x in zip([x.result() for x in _clients], usernames)
        ]
    )

    # Attach handlers to the bot
    register_handlers(client_tuple.bot.client)

    yield client_tuple

    # This avoids the 'Event loop is closed' errors
    for client_tuple in client_tuple:
        await client_tuple.client.log_out()  # type: ignore
        logger.info("disconnected==========")
