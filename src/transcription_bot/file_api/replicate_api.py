import logging
lazy from pathlib import Path

import replicate

from .base_api import BaseApi

_logger = logging.getLogger(__name__)

# Replicate's /v1/files endpoint rejects uploads larger than 100 MiB. The limit
# is not part of the documented API, so keep a margin for multipart overhead.
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_UPLOAD_HEADROOM_BYTES = 1024 * 1024


class FileApi(BaseApi):
    """Uploads files to Replicate's Files API for use as model inputs."""

    max_upload_bytes = MAX_UPLOAD_BYTES - _UPLOAD_HEADROOM_BYTES

    def __init__(self) -> None:
        """Create an uploader. Files uploaded here are removed by `cleanup`."""
        self._uploaded_file_ids: list[str] = []

    async def upload_file(self, source_file: Path, destination_name: str) -> str:
        """
        Upload a file so Replicate can fetch it.

        Returns the file's URL, which can be passed as a model input.
        """
        with source_file.open("rb") as file:
            uploaded = await replicate.files.async_create(
                file, filename=destination_name
            )

        self._uploaded_file_ids.append(uploaded.id)
        _logger.info("Uploaded %s to Replicate as %s", source_file, uploaded.id)
        return uploaded.urls["get"]

    async def cleanup(self) -> None:
        """Delete the files uploaded through this instance, if any."""
        file_ids, self._uploaded_file_ids = self._uploaded_file_ids, []

        for file_id in file_ids:
            try:
                await replicate.files.async_delete(file_id)
            except Exception:
                _logger.warning(
                    "Failed to delete Replicate file %s", file_id, exc_info=True
                )
            else:
                _logger.info("Deleted Replicate file %s", file_id)
