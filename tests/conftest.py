"""Test setup: supply placeholder settings and skip MinIO tests when it is not configured."""

import os

import pytest

# Settings that the app requires but that tests should not need real values for
_SETTINGS_PLACEHOLDERS = {
    "API_HASH": "test-api-hash",
    "API_ID": "0",
    "HF_TOKEN": "test-hf-token",
    "MINIO_ACCESS_KEY": "test-minio-access-key",
    "MINIO_BUCKET": "test-minio-bucket",
    "MINIO_HOST": "localhost:9000",
    "MINIO_SECRET_KEY": "test-minio-secret-key",
    "MY_USERNAME": "@test",
    "OPENAI_API_KEY": "test-openai-api-key",
    "OPENAI_BASE_URL": "http://localhost:8080",
    "OPENAI_MODEL_NAME": "test-model",
    "REPLICATE_API_TOKEN": "test-replicate-token",
    "SESSION_FILE": "test.session",
    "TOKEN": "000000000:test-token",
    "TZ": "UTC",
}

_MINIO_SETTINGS = ("MINIO_ACCESS_KEY", "MINIO_BUCKET", "MINIO_HOST", "MINIO_SECRET_KEY")

# Checked before the placeholders are applied, so real credentials still enable the tests
MINIO_CONFIGURED = all(os.environ.get(name) for name in _MINIO_SETTINGS)

for _name, _value in _SETTINGS_PLACEHOLDERS.items():
    os.environ.setdefault(_name, _value)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip integration tests when no MinIO instance is configured."""
    if MINIO_CONFIGURED:
        return

    skip = pytest.mark.skip(
        reason="MinIO is not configured (set the MINIO_* environment variables)"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
