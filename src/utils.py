from datetime import timedelta


def format_hhmmss(s: int):
    delta = timedelta(seconds=s)
    hours = delta.days * 24 + delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"
