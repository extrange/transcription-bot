import asyncio
import logging
import random
from typing import NamedTuple

import pytest
import pytest_asyncio
import uvloop
from pytest_asyncio import is_async_test
from telethon import TelegramClient, functions
from utils import get_random_string

from transcriptionbot.bot.credentials import Credentials
from transcriptionbot.bot.handlers import register_handlers

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_USERNAME = get_random_string()
ME_USERNAME = get_random_string()
OTHER_USERNAME = get_random_string()


class ClientGroup(NamedTuple):
    bot: TelegramClient
    me: TelegramClient
    other: TelegramClient


def pytest_collection_modifyitems(items):
    """
    Mark all async test_* functions with session scope
    """
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session")
def event_loop_policy():
    """
    Use the same event loop for all tests (session scope)
    """
    return uvloop.EventLoopPolicy()


async def setup_account(test_phone_number: str, username: str):
    """
    Setup a telegram test account with a username.
    Rotates between random DCs and phone numbers.
    See https://core.telegram.org/api/auth#test-accounts
    """

    client = TelegramClient(None, Credentials.API_ID, Credentials.API_HASH)  # type: ignore
    client.session.set_dc(2, "149.154.167.40", 80)  # type: ignore
    await client.start(phone=lambda: test_phone_number, code_callback=lambda: "22222")  # type: ignore

    await client(functions.account.UpdateUsernameRequest(username=username))
    logger.info(f"TEST: Using {test_phone_number=}, {username=}")
    return client


@pytest_asyncio.fixture(scope="session")
async def clients():
    """
    The same 3 accounts are reused for the whole session.
    Also changes the value of MY_USERNAME
    """
    # Change MY_USERNAME to MY_USERNAME
    Credentials.MY_USERNAME = ME_USERNAME

    _clients = []
    numbers = list(range(0, 10_000))
    random.shuffle(numbers)
    usernames = [BOT_USERNAME, ME_USERNAME, OTHER_USERNAME]

    for i in range(3):
        _clients.append(setup_account(f"999662{numbers[i]:0>4}", usernames[i]))

    client_tuple = ClientGroup(*(await asyncio.gather(*_clients)))

    # Attach handlers to the bot
    register_handlers(client_tuple.bot)

    yield client_tuple

    # This avoids the 'Event loop is closed' errors
    for client in client_tuple:
        await client.disconnect()  # type: ignore
