import json
import time
from functools import partial
from pathlib import Path

import pytest
from transcription_bot.file_api.minio_api import FileApi
from transcription_bot.file_api.policy import Policy
from transcription_bot.settings import Settings


@pytest.fixture()
def partial_client() -> partial[FileApi]:
    return partial(
        FileApi,
        host=Settings.MINIO_HOST,
        access_key=Settings.MINIO_ACCESS_KEY.get_secret_value(),
        secret_key=Settings.MINIO_SECRET_KEY.get_secret_value(),
    )


@pytest.fixture()
def client(partial_client: partial[FileApi]) -> FileApi:
    return partial_client(
        bucket_name=Settings.MINIO_BUCKET,
        default_policy=Policy.public_read_only(),
    )


@pytest.fixture()
def test_file_path(tmp_path: Path):
    _path = tmp_path / "test_file"
    with _path.open("w") as f:
        f.write("test file contents")
    return _path


def test_bucket_created_if_not_exists(partial_client: partial[FileApi]):
    """Create a test bucket"""
    bucket_name = str(time.time())
    client = partial_client(
        bucket_name=bucket_name,
        default_policy=Policy.public_read_only(),
    )
    assert client.client.bucket_exists(bucket_name)
    client.client.remove_bucket(bucket_name)


def test_policy_replaced_correctly():
    assert FileApi._construct_policy(
        Policy.public_read_only(),
        "test_bucket",
    ) != json.dumps(Policy.public_read_only())


def test_minio_upload(client: FileApi, test_file_path: Path):
    object_name = "my-test-file"
    client.upload_file(test_file_path, object_name)
    assert client.client.get_object(client.bucket_name, object_name)
    client.client.remove_object(client.bucket_name, object_name)
