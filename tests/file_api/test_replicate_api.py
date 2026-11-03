from unittest.mock import AsyncMock, MagicMock, patch
lazy from pathlib import Path

import pytest

from transcription_bot.file_api.replicate_api import FileApi

_FILE_ID = "file-123"
_FILE_URL = f"https://api.replicate.com/v1/files/{_FILE_ID}"


@pytest.fixture
def test_file_path(tmp_path: Path) -> Path:
    path = tmp_path / "test_file.mp3"
    path.write_bytes(b"test file contents")
    return path


@pytest.fixture
def uploaded_file() -> MagicMock:
    file = MagicMock()
    file.id = _FILE_ID
    file.urls = {"get": _FILE_URL}
    return file


async def test_upload_file_returns_replicate_url(
    test_file_path: Path, uploaded_file: MagicMock
):
    create = AsyncMock(return_value=uploaded_file)
    with patch("replicate.files.async_create", create):
        api = FileApi()
        url = await api.upload_file(test_file_path, "destination.mp3")

    assert url == _FILE_URL
    create.assert_awaited_once()
    assert create.await_args is not None
    assert create.await_args.kwargs["filename"] == "destination.mp3"


async def test_cleanup_deletes_uploaded_file(
    test_file_path: Path, uploaded_file: MagicMock
):
    create = AsyncMock(return_value=uploaded_file)
    delete = AsyncMock()
    with (
        patch("replicate.files.async_create", create),
        patch("replicate.files.async_delete", delete),
    ):
        api = FileApi()
        await api.upload_file(test_file_path, "destination.mp3")
        await api.cleanup()

    delete.assert_awaited_once_with(_FILE_ID)


async def test_cleanup_deletes_every_uploaded_file(
    test_file_path: Path, uploaded_file: MagicMock
):
    create = AsyncMock(return_value=uploaded_file)
    delete = AsyncMock()
    with (
        patch("replicate.files.async_create", create),
        patch("replicate.files.async_delete", delete),
    ):
        api = FileApi()
        await api.upload_file(test_file_path, "first.mp3")
        await api.upload_file(test_file_path, "second.mp3")
        await api.cleanup()

    assert delete.await_count == 2


async def test_cleanup_is_idempotent(test_file_path: Path, uploaded_file: MagicMock):
    create = AsyncMock(return_value=uploaded_file)
    delete = AsyncMock()
    with (
        patch("replicate.files.async_create", create),
        patch("replicate.files.async_delete", delete),
    ):
        api = FileApi()
        await api.upload_file(test_file_path, "destination.mp3")
        await api.cleanup()
        await api.cleanup()

    delete.assert_awaited_once()


async def test_cleanup_without_upload_does_nothing():
    delete = AsyncMock()
    with patch("replicate.files.async_delete", delete):
        await FileApi().cleanup()

    delete.assert_not_awaited()


async def test_cleanup_swallows_delete_errors(
    test_file_path: Path, uploaded_file: MagicMock
):
    delete = AsyncMock(side_effect=RuntimeError("delete failed"))
    create = AsyncMock(return_value=uploaded_file)
    with (
        patch("replicate.files.async_create", create),
        patch("replicate.files.async_delete", delete),
    ):
        api = FileApi()
        await api.upload_file(test_file_path, "destination.mp3")

        # Cleanup failures must not mask the transcription result.
        await api.cleanup()
