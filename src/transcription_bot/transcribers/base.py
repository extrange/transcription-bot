from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Concatenate

from transcription_bot.types import PredictionStatus


class BaseTranscriber(ABC):
    """Base class for classes implementing external audio transcription."""

    @abstractmethod
    async def send_job(
        self,
        file_url: str,
        log_cb: Callable[Concatenate[str, ...], Coroutine] | None,
        update_interval: int = 3,
    ) -> tuple[str | None, PredictionStatus]:
        """Transcribe and diarize an audio file."""
