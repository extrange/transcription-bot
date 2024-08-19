import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Concatenate

import replicate
import replicate.version
from replicate.prediction import Prediction

from .types import ModelParams, ModelParamsWithoutUrl, Output, PredictionStatus

_logger = logging.getLogger(__name__)


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


class ReplicateTranscriber(BaseTranscriber):
    """Uses thomasmol/whisper-diarization."""

    model_name = "thomasmol/whisper-diarization"

    def __init__(self, version: str, params: ModelParamsWithoutUrl) -> None:
        """Prepare a prediction pipeline."""
        self.model_version = version
        self.params = params
        super().__init__()

    def _construct_model(self) -> replicate.version.Version:
        model = replicate.models.get(self.model_name)
        return model.versions.get(self.model_version)

    @staticmethod
    def _is_prediction_running(prediction: Prediction) -> bool:
        return prediction.status in ("starting", "processing")

    @staticmethod
    async def _update_progress(
        log_cb: Callable[Concatenate[str, ...], Coroutine],
        update_interval: int,
        prediction: Prediction,
    ) -> None:
        tasks = []

        while ReplicateTranscriber._is_prediction_running(prediction):
            logs = prediction.logs
            if logs:
                tasks.append(asyncio.create_task(log_cb(logs)))
            await asyncio.sleep(update_interval)
            await prediction.async_reload()

    @staticmethod
    def _process_output(output: Output) -> str:
        return "\n\n".join([f"{s.speaker}: {s.text}" for s in output.segments])

    async def send_job(
        self,
        file_url: str,
        log_cb: Callable[Concatenate[str, ...], Coroutine] | None,
        update_interval: int = 3,
    ) -> tuple[str | None, PredictionStatus]:
        """
        Start a transcription job asynchronously.

        Optionally, provide a callback which will be called with the current log lines, called every `update_interval` seconds.
        """
        version = self._construct_model()
        params_with_url = ModelParams(**self.params.model_dump(), file_url=file_url)
        prediction = await replicate.predictions.async_create(
            version,
            input=params_with_url.model_dump(),
        )

        _logger.info("Prediction created for file %s", file_url)

        if log_cb:
            self.update_task = asyncio.create_task(
                self._update_progress(log_cb, update_interval, prediction),
            )

        await prediction.async_wait()
        processed_output = (
            self._process_output(prediction.output) if prediction.output else None
        )
        return (processed_output, prediction.status)
