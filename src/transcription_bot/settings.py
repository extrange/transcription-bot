import logging
from pathlib import Path

from pydantic import (
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings


class _Settings(BaseSettings):
    SESSION_FILE: Path
    TOKEN: SecretStr
    API_HASH: SecretStr
    API_ID: int
    MY_USERNAME: SecretStr
    REPLICATE_API_TOKEN: SecretStr
    MINIO_ACCESS_KEY: SecretStr
    MINIO_SECRET_KEY: SecretStr
    MINIO_HOST: str
    MINIO_BUCKET: str
    MODEL_VERSION: str

    TZ: str
    LOG_LEVEL: str = "INFO"

    @field_validator("LOG_LEVEL")
    @classmethod
    def _check_log_level(cls, v: str) -> str:
        if v not in logging.getLevelNamesMapping():
            msg = f"'{v}' is not a valid log level"
            raise ValueError(msg)
        return v


Settings = _Settings.model_validate({})
