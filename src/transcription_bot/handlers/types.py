class NoMediaFileError(Exception):
    """No media file found in the message."""


class DownloadFailedError(Exception):
    """Failed to download file."""


class ParseError(Exception):
    """Failed to parse the file."""


class TranscriptionFailedError(Exception):
    """Prediction failed."""


class TranscriptionTimeoutError(Exception):
    """Failed > 3 attempts to transcribe."""


class ReencodeError(Exception):
    """Failed to re-encode the audio."""


class FileTooLargeError(Exception):
    """Audio does not fit the upload limit even after re-encoding."""
