import pytest
import uvloop
from telethon import TelegramClient
from transcriptionbot.bot.credentials import credentials

@pytest.fixture(scope="session")
def event_loop_policy():
    return uvloop.EventLoopPolicy()


@pytest.fixture(scope="session")
async def bot():
    """Setup the telegram bot instance"""
    

    
    client = TelegramClient(None, api_id, api_hash)
    client.session.set_dc(dc_id, '149.154.167.40', 80)
    print("aoeu")

@pytest.fixture(scope="session")
async def human():
    client = TelegramClient(None, credentials["API_ID"], credentials["API_HASH"]) # type: ignore