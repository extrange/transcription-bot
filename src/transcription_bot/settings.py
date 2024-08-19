from pydantic import SecretStr
from pydantic_settings import BaseSettings


class _Settings(BaseSettings):
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


Settings = _Settings.model_validate({})
