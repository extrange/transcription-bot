from transcription_bot.utils.format_hhmmss import format_hhmmss


def test_zero():
    assert format_hhmmss(0) == "0:00:00"


def test_seconds_only():
    assert format_hhmmss(59) == "0:00:59"


def test_minutes_and_seconds():
    assert format_hhmmss(100) == "0:01:40"


def test_hours():
    assert format_hhmmss(3725) == "1:02:05"


def test_more_than_a_day():
    assert format_hhmmss(90061) == "25:01:01"


def test_truncates_fractions_of_a_second():
    assert format_hhmmss(100.9) == "0:01:40"
