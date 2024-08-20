import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Concatenate

import httpx
import replicate
import replicate.version
from replicate.prediction import Prediction

from transcription_bot.transcribers.base import BaseTranscriber
from transcription_bot.types import (
    ModelParams,
    ModelParamsWithoutUrl,
    Output,
    PredictionStatus,
)

_logger = logging.getLogger(__name__)


class MaxAttemptsExceededError(Exception):
    """Too many attempts to connect to replicate failed."""


class ReplicateTranscriber(BaseTranscriber):
    """Uses thomasmol/whisper-diarization."""

    model_name = "thomasmol/whisper-diarization"

    def __init__(self, version: str, params: ModelParamsWithoutUrl) -> None:
        """Prepare a prediction pipeline."""
        self.model_version = version
        self.params = params
        self.prediction = None
        super().__init__()

    def _construct_model(self) -> replicate.version.Version:
        model = replicate.models.get(self.model_name)
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
            _logger.info("logs: %s", logs)
            task = asyncio.create_task(
                log_cb(f"{prediction.status}: {logs or "Waiting in queue..."}")
            )
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            await asyncio.sleep(update_interval)
            await prediction.async_reload()

        _logger.info("_update_progress exited.")

    @staticmethod
    def _process_output(output: Output) -> str:
        return "\n\n".join([f"{s.speaker}: {s.text}" for s in output.segments])

    @staticmethod
    async def cancel(pred_id: str) -> None:
        """Cancel a running prediction."""
        await replicate.predictions.async_cancel(pred_id)

    async def get_result(self) -> tuple[str | None, PredictionStatus]:
        """Wait for result to be done."""
        if not self.prediction:
            msg = "No prediction running!"
            raise ValueError(msg)

        await self.prediction.async_wait()
        processed_output = (
            self._process_output(Output.model_validate(self.prediction.output))
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
        params_with_url = ModelParams(**self.params.model_dump(), file_url=file_url)

        async def get_prediction(max_attempts: int = 3) -> Prediction:
            attempts = 0
            prediction = None
            while not prediction:
                if attempts > max_attempts:
                    raise MaxAttemptsExceededError
                try:
                    prediction = await replicate.predictions.async_create(
                        version,
                        input=params_with_url.model_dump(exclude_none=True),
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
