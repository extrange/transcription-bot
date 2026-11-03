import copy
import json
import logging
from datetime import timedelta
from functools import partial
lazy from pathlib import Path

from minio import Minio
from minio.error import S3Error

from .base_api import BaseApi
from .utils import apply_recursively

_logger = logging.getLogger(__name__)


class FileApi(BaseApi):
    """Minio File Storage operations."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        host: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        default_policy: dict | None,
        presign_expiry_days: int = 7,
    ) -> None:
        """
        Initialize the FileApi client to perform Minio File Storage operations.

        Creates the bucket if it did not exist, then enforces `default_policy`.

        `default_policy`: Anonymous bucket policy to apply on startup, or None to
        remove any existing policy so only credentialed access is allowed.

        `presign_expiry_days`: Lifetime of the presigned URLs returned by
        `upload_file`. S3 and MinIO cap presigned GET URLs at 7 days.
        """
        self.host = host
        self.bucket_name = bucket_name
        self.presign_expiry_days = presign_expiry_days
        self.default_policy = (
            FileApi._construct_policy(default_policy, bucket_name)
            if default_policy is not None
            else None
        )
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

    def _set_bucket_policy(self) -> None:
        if self.default_policy is None:
            self._clear_bucket_policy()
            return
        self.client.set_bucket_policy(self.bucket_name, self.default_policy)
        _logger.info(
            "Set bucket policy on %s to %s", self.bucket_name, self.default_policy
        )

    def _clear_bucket_policy(self) -> None:
        """Remove the bucket policy, leaving only credentialed (or presigned) access."""
        try:
            self.client.delete_bucket_policy(self.bucket_name)
        except S3Error as e:
            # Nothing to remove; the bucket is already private.
            if e.code != "NoSuchBucketPolicy":
                raise
        _logger.info(
            "Cleared bucket policy on %s; anonymous access is disabled",
            self.bucket_name,
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

        Returns a presigned URL for the uploaded object, valid for
        `presign_expiry_days`. Presigned URLs are bearer tokens: anyone holding
        the link can fetch the object until it expires, but the bucket itself
        stays private.
        """
        self.client.fput_object(
            self.bucket_name,
            destination_name,
            str(source_file),
        )
        _logger.info(
            "Uploaded file %s as object %s to bucket %s",
            source_file,
            destination_name,
            self.bucket_name,
        )
        return self.client.presigned_get_object(
            self.bucket_name,
            destination_name,
            expires=timedelta(days=self.presign_expiry_days),
        )

    def download_file(self, object_name: str, destination_path: Path) -> None:
        """Download a file from the bucket."""
        self.client.fget_object(self.bucket_name, object_name, str(destination_path))
