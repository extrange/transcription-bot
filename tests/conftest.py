import asyncio
from transcriptionbot.bot.handlers import register_handlers
from transcriptionbot.bot.credentials import Credentials
import logging
import os
import random
import string
from typing import NamedTuple

import pytest
import pytest_asyncio
import uvloop
from pytest_asyncio import is_async_test
from telethon import TelegramClient, functions

# Don't import transcriptionbot here, so we can modify environment variables for MY_USERNAME


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class ClientGroup(NamedTuple):
    bot: TelegramClient
    me: TelegramClient
    other: TelegramClient


def get_random_string(length=10):
    # Exclude digits because Telegram usernames cannot start with a digit
    return "".join(random.choices(string.ascii_lowercase, k=length))


BOT_USERNAME = get_random_string()
ME_USERNAME = get_random_string()
OTHER_USERNAME = get_random_string()


def pytest_collection_modifyitems(items):
    """
    Mark all async test_* functions with session scope
    Note: pytest_asyncio should be in auto mode
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
    See https://core.telegram.org/api/auth#test-accounts
    """

    client = TelegramClient(None, Credentials.API_ID, Credentials.API_HASH)  # type: ignore
    client.session.set_dc(2, "149.154.167.40", 80)  # type: ignore
    await client.start(phone=lambda: test_phone_number, code_callback=lambda: "22222")  # type: ignore

    await client(functions.account.UpdateUsernameRequest(username=username))
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
    starting_number = random.randint(0, 9999)
    usernames = [BOT_USERNAME, ME_USERNAME, OTHER_USERNAME]

    for i in range(3):
        _clients.append(setup_account(f"999662{starting_number:0>4}", usernames[i]))
        starting_number = (starting_number + 1) % 10_000

    client_tuple = ClientGroup(*(await asyncio.gather(*_clients)))

    # Attach handlers to the bot
    register_handlers(client_tuple.bot)

    yield client_tuple

    # This avoids the 'Event loop is closed' errors
    for client in client_tuple:
        await client.disconnect()  # type: ignore
