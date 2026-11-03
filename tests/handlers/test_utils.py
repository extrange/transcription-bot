from transcription_bot.handlers.utils import fit_audio_bitrate_kbps

_MAX_BYTES = 100 * 1024 * 1024


def test_fit_audio_bitrate_caps_at_max_for_short_audio():
    assert fit_audio_bitrate_kbps(60, _MAX_BYTES) == 32


def test_fit_audio_bitrate_lowers_bitrate_for_long_audio():
    # ~11 hours of audio: only ~19 kbps fits within the upload limit.
    assert fit_audio_bitrate_kbps(40_000, _MAX_BYTES) == 19


def test_fit_audio_bitrate_does_not_go_below_minimum():
    # ~28 hours of audio: the minimum is returned even though it will not fit.
    assert fit_audio_bitrate_kbps(100_000, _MAX_BYTES) == 8


def test_fit_audio_bitrate_for_unknown_duration_uses_max():
    assert fit_audio_bitrate_kbps(0, _MAX_BYTES) == 32
