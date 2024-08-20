from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Concatenate

from transcription_bot.types import PredictionStatus


class BaseTranscriber(ABC):
    """Base class for classes implementing external audio transcription."""

    @staticmethod
    @abstractmethod
    async def cancel(pred_id: str) -> None:
        """Cancel a running prediction."""

    @abstractmethod
    async def get_result(self) -> tuple[str | None, PredictionStatus]:
        """Wait for prediction result to complete."""

    @abstractmethod
    async def send_job(
        self,
        file_url: str,
        log_cb: Callable[Concatenate[str, ...], Coroutine] | None,
        update_interval: int = 3,
    ) -> str:
        """Transcribe and diarize an audio file."""
