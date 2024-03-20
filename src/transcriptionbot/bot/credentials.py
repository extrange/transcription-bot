import os


class Credentials:
    MY_USERNAME = os.environ["MY_USERNAME"]
    API_HASH = os.environ["API_HASH"]
    API_ID = int(os.environ["API_ID"])
