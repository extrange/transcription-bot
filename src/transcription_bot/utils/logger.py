import logging

from transcription_bot.settings import Settings


def setup_logging() -> None:
    """Configure logging."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.getLevelNamesMapping()[Settings.LOG_LEVEL],
    )
