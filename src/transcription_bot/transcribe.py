import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Concatenate

import replicate
import replicate.version
from pydantic import HttpUrl
from replicate.prediction import Prediction

from .types import ModelParams, ModelParamsWithoutUrl, Output


class BaseTranscriber(ABC):
    """Base class for classes implementing external audio transcription."""

    @abstractmethod
    async def send_job(self, audio: Path) -> None:
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
    async def _wait_until_done(
        done_cb: Callable[Concatenate[Output | None, ...]],
        prediction: Prediction,
    ) -> None:
        await prediction.async_wait()
        await done_cb(prediction)
        # TODO return something like jobstatus instead of None
        # TODO why is prediction accepted here

    async def send_job(
        self,
        file_url: HttpUrl,
        done_cb: Callable[Concatenate[Output | None, ...]],
        log_cb: Callable[Concatenate[str, ...], Coroutine] | None,
        update_interval: int = 3,
    ) -> None:
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

        if log_cb:
            self.update_task = asyncio.create_task(
                self._update_progress(log_cb, update_interval, prediction),
            )
        self.done_task = asyncio.create_task(self._wait_until_done(done_cb, prediction))
