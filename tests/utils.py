import random
import string


def get_random_string(length: int = 10):
    # Exclude digits because Telegram usernames cannot start with a digit
    return "".join(random.choices(string.ascii_lowercase, k=length))  # noqa: S311
