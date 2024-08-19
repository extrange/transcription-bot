class NoMediaFileError(Exception):
    """No media file found in the message."""


class DownloadFailedError(Exception):
    """Failed to download file."""


class ParseError(Exception):
    """Failed to parse the file."""


class TranscriptionFailedError(Exception):
    """Prediction failed."""
