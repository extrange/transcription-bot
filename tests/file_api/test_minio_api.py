import json
import time
from functools import partial
lazy from pathlib import Path

import pytest
from minio.error import S3Error

from transcription_bot.file_api.minio_api import FileApi
from transcription_bot.file_api.policy import Policy
from transcription_bot.settings import Settings


@pytest.fixture
def partial_client() -> partial[FileApi]:
    return partial(
        FileApi,
        host=Settings.MINIO_HOST,
        access_key=Settings.MINIO_ACCESS_KEY.get_secret_value(),
        secret_key=Settings.MINIO_SECRET_KEY.get_secret_value(),
    )


@pytest.fixture
def client(partial_client: partial[FileApi]) -> FileApi:
    return partial_client(
        bucket_name=Settings.MINIO_BUCKET,
        default_policy=Policy.none(),
    )


@pytest.fixture
def test_file_path(tmp_path: Path):
    _path = tmp_path / "test_file"
    with _path.open("w") as f:
        f.write("test file contents")
    return _path


@pytest.mark.integration
def test_bucket_created_if_not_exists(partial_client: partial[FileApi]):
    """Create a test bucket"""
    bucket_name = str(time.time())
    client = partial_client(
        bucket_name=bucket_name,
        default_policy=Policy.none(),
    )
    assert client.client.bucket_exists(bucket_name)
    client.client.remove_bucket(bucket_name)


def test_policy_replaced_correctly():
    assert FileApi._construct_policy(
        Policy.public_read_only(),
        "test_bucket",
    ) != json.dumps(Policy.public_read_only())


@pytest.mark.integration
def test_minio_upload(client: FileApi, test_file_path: Path):
    object_name = "my-test-file"
    client.upload_file(test_file_path, object_name)
    assert client.client.get_object(client.bucket_name, object_name)
    client.client.remove_object(client.bucket_name, object_name)


@pytest.mark.integration
def test_upload_returns_presigned_url(client: FileApi, test_file_path: Path):
    """The URL handed to Replicate and the user must be presigned, not public."""
    object_name = "my-test-file-presigned"
    url = client.upload_file(test_file_path, object_name)
    try:
        assert url.startswith("https://")
        assert "X-Amz-Signature=" in url
        assert "X-Amz-Expires=" in url
    finally:
        client.client.remove_object(client.bucket_name, object_name)


@pytest.mark.integration
def test_bucket_has_no_anonymous_policy(client: FileApi):
    """`Policy.none()` must strip the policy, so the bucket is not listable."""
    with pytest.raises(S3Error) as exc_info:
        client.client.get_bucket_policy(client.bucket_name)
    assert exc_info.value.code == "NoSuchBucketPolicy"
