from abc import ABC, abstractmethod
from pathlib import Path


class BaseApi(ABC):
    """Base API class for classes providing file storage operations."""

    @abstractmethod
    def upload_file(self, source_file: Path, destination_name: str) -> str:
        """Upload a file to the storage."""

    @abstractmethod
    def download_file(self, object_name: str, destination_path: Path) -> None:
        """Download a file from the storage."""
