"""Runtime settings, read from environment variables.

`REPLICATE_API_TOKEN` is intentionally absent: the Replicate SDK reads it
directly from the environment.
"""

import logging
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    """All runtime configuration, supplied as environment variables."""

    model_config = SettingsConfigDict(extra="ignore")

    # Required: no sensible default.
    API_HASH: SecretStr
    API_ID: int
    MINIO_ACCESS_KEY: SecretStr
    MINIO_SECRET_KEY: SecretStr
    MY_USERNAME: SecretStr
    OPENAI_API_KEY: SecretStr

    # Optional: sane defaults, overridable from the environment.
    SESSION_FILE: Path = Path("credentials/account.session")
    MINIO_HOST: str = "localhost:9000"
    MINIO_BUCKET: str = "transcription-bot"
    MODEL_VERSION: str = Field(
        default="latest",
        description=(
            "Replicate model version to use for transcription. Use 'latest' to "
            "always run the model's newest version, or pin a specific version "
            "hash for reproducible results."
        ),
    )
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    TZ: str = "Asia/Singapore"
    LOG_LEVEL: str = "INFO"

    @field_validator("LOG_LEVEL")
    @classmethod
    def _check_log_level(cls, v: str) -> str:
        if v not in logging.getLevelNamesMapping():
            msg = f"'{v}' is not a valid log level"
            raise ValueError(msg)
        return v


Settings = _Settings.model_validate({})
