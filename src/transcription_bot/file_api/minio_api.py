import copy
import json
import logging
from functools import partial
from pathlib import Path

from minio import Minio

from .base_api import BaseApi
from .utils import apply_recursively

_logger = logging.getLogger(__name__)


class FileApi(BaseApi):
    """Minio File Storage operations."""

    def __init__(
        self,
        host: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        default_policy: dict,
    ) -> None:
        """Initialize the FileApi client to perform Minio File Storage operations. Creates the bucket if it did not exist."""
        self.host = host
        self.bucket_name = bucket_name
        self.default_policy = FileApi._construct_policy(default_policy, bucket_name)
        self.client = Minio(str(host), access_key=access_key, secret_key=secret_key)
        self._create_bucket_if_not_exists()

    @staticmethod
    def _replace_bucket_name(val: str, bucket_name: str) -> str:
        return val.format(bucket=bucket_name)

    @staticmethod
    def _construct_policy(policy: dict, bucket_name: str) -> str:
        _policy = copy.deepcopy(policy)
        apply_recursively(
            partial(FileApi._replace_bucket_name, bucket_name=bucket_name),
            _policy,
            lambda v: isinstance(v, str),
        )
        return json.dumps(_policy, separators=(",", ":"))

    def _construct_minio_url(self, destination_file: str) -> str:
        return f"{self.host}/{self.bucket_name}/{destination_file}"

    def _set_bucket_policy(self) -> None:
        self.client.set_bucket_policy(self.bucket_name, self.default_policy)
        _logger.info(
            "Policy on bucket %s does not match default: setting policy to default_policy",
            self.default_policy,
        )

    def _create_bucket_if_not_exists(self) -> None:
        bucket_name = self.bucket_name
        found = self.client.bucket_exists(bucket_name)
        if not found:
            self.client.make_bucket(bucket_name)
            _logger.info("Created bucket %s", bucket_name)
        else:
            _logger.info("Bucket %s already exists, skipping creation", bucket_name)
        self._set_bucket_policy()

    def upload_file(self, source_file: Path, destination_name: str) -> str:
        """
        Upload a file to the bucket on this class.

        Returns the Minio URL of the uploaded file.
        """
        self.client.fput_object(
            self.bucket_name,
            destination_name,
            str(source_file),
        )
        logging.info(
            "Uploaded file %s as object %s to bucket %s",
            source_file,
            destination_name,
            self.bucket_name,
        )
        return self._construct_minio_url(destination_name)

    def download_file(self, object_name: str, destination_path: Path) -> None:
        """Download a file from the bucket."""
        self.client.fget_object(self.bucket_name, object_name, str(destination_path))
