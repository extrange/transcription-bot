import asyncio
import logging
from abc import abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any, Concatenate

import httpx
import replicate
import replicate.version
from replicate.prediction import Prediction

from transcription_bot.handlers.types import TranscriptionTimeoutError
from transcription_bot.transcribers.base import BaseTranscriber
from transcription_bot.types import (
    PredictionStatus,
)

_logger = logging.getLogger(__name__)


class MaxAttemptsExceededError(Exception):
    """Too many attempts to connect to replicate failed."""


class ReplicateTranscriberBase(BaseTranscriber):
    """Base class for transcription using Replicate models."""

    def __init__(self, version: str) -> None:
        """Prepare a prediction pipeline."""
        self.model_version = version
        self.prediction = None
        super().__init__()

    @abstractmethod
    def _get_model_name(self) -> str:
        """Return the model name as found on Replicate."""

    @abstractmethod
    def _get_model_params(self, file_url: str) -> dict[str, Any]:
        """
        Construct the model parameters for the model.

        file_url: URL of the uploaded file to be transcribed, accessed by Replicate.
        """

    @abstractmethod
    def _process_output(self, model_output: Any) -> str:
        """Process the output from a model."""

    def _construct_model(self) -> replicate.version.Version:
        model = replicate.models.get(self._get_model_name())
        _logger.info("Constructed Replicate model %s", model.name)
        return model.versions.get(self.model_version)

    def _is_prediction_running(self) -> bool:
        if not self.prediction:
            return False
        return self.prediction.status in ("starting", "processing")

    async def _update_progress(
        self,
        log_cb: Callable[Concatenate[str, ...], Coroutine],
        update_interval: int,
        prediction: Prediction,
    ) -> None:
        self.tasks = set()

        while self._is_prediction_running():
            logs = prediction.logs
            _logger.info("Prediciton logs: %s", logs)
            task = asyncio.create_task(
                log_cb(f"{prediction.status}: {logs or "Waiting in queue..."}")
            )
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            await asyncio.sleep(update_interval)
            await prediction.async_reload()

        _logger.info("_update_progress exited.")

    @staticmethod
    async def cancel(pred_id: str) -> None:
        """Cancel a running prediction."""
        await replicate.predictions.async_cancel(pred_id)

    async def get_result(
        self, max_attempts: int = 3
    ) -> tuple[str | None, PredictionStatus]:
        """Wait for result to be done."""
        if not self.prediction:
            msg = "No prediction running!"
            raise ValueError(msg)

        success = False
        attempts = 0
        while not success:
            if attempts > max_attempts:
                raise TranscriptionTimeoutError
            try:
                await self.prediction.async_wait()
                success = True
            except httpx.ConnectTimeout:
                _logger.info(
                    "Failed transcription due to httpx.ConnectTimeout, retrying"
                )
                attempts += 1

        _logger.info("Prediction metrics: %s", self.prediction.metrics)

        processed_output = (
            self._process_output(self.prediction.output)
            if self.prediction.output
            else None
        )
        return (processed_output, self.prediction.status)

    async def send_job(
        self,
        file_url: str,
        log_cb: Callable[Concatenate[str, ...], Coroutine] | None,
        update_interval: int = 3,
    ) -> str:
        """
        Start a transcription job asynchronously.

        Returns the id of the prediction that can be used for cancellation.

        Optionally, provide a callback which will be called with the current log lines, called every `update_interval` seconds.
        """
        version = self._construct_model()

        async def get_prediction(max_attempts: int = 3) -> Prediction:
            attempts = 0
            prediction = None
            while not prediction:
                if attempts > max_attempts:
                    raise MaxAttemptsExceededError
                try:
                    prediction = await replicate.predictions.async_create(
                        version, input=self._get_model_params(file_url)
                    )

                except httpx.ConnectTimeout:
                    _logger.warning(
                        "Attempt %s: Failed to send file to replicate, retrying",
                        attempts + 1,
                    )
                    attempts += 1
            return prediction

        prediction = await get_prediction()
        _logger.info("Prediction created for file %s", file_url)

        if log_cb:
            self.update_task = asyncio.create_task(
                self._update_progress(log_cb, update_interval, prediction),
            )
            _logger.info("Created task for logging callback.")

        self.prediction = prediction
        return prediction.id
