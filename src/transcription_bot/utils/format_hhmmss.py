"""Format a duration in seconds as H:MM:SS."""

from datetime import timedelta


def format_hhmmss(seconds: float) -> str:
    """Format seconds into H:MM:SS format.

    ```python
    format_hhmmss(100)  # "0:01:40"
    ```
    """
    delta = timedelta(seconds=seconds)
    hours = delta.days * 24 + delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    secs = delta.seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"
