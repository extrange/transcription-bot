import os
from typing import NamedTuple


class __Credentials(NamedTuple):
    MY_CHAT_ID = int(os.environ["MY_CHAT_ID"])
    API_HASH = os.environ["API_HASH"]
    API_ID = int(os.environ["API_ID"])


credentials = __Credentials()
