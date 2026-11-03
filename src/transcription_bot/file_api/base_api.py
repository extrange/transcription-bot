from abc import ABC, abstractmethod
lazy from pathlib import Path


class BaseApi(ABC):
    """Base API class for classes providing file storage operations."""

    max_upload_bytes: int
    """Largest file this backend accepts, in bytes."""

    @abstractmethod
    async def upload_file(self, source_file: Path, destination_name: str) -> str:
        """Upload a file and return a URL that external services can fetch."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Delete any files uploaded through this instance."""
