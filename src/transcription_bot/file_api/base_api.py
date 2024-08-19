from abc import ABC, abstractmethod


class BaseApi(ABC):
    """Base API class for classes providing file storage operations."""

    @abstractmethod
    def upload_file(self) -> str:
        """Upload a file to the storage."""

    @abstractmethod
    def download_file(self) -> str:
        """Download a file from the storage."""
