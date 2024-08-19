from typing import Literal

from pydantic import BaseModel, HttpUrl, PositiveInt


class Word(BaseModel):
    """Information about a single word from a segment."""

    end: float
    probability: float
    start: float
    word: str


class Segment(BaseModel):
    """Contains speaker information."""

    avg_logprob: float
    end: float
    speaker: str
    start: float
    text: str
    words: list[Word]


class Output(BaseModel):
    """Output from thomasmol/whisper-diarization."""

    language: str
    num_speakers: int
    segments: list[Segment]


class ModelParamsWithoutUrl(BaseModel):
    """
    Parameters as from https://github.com/thomasmol/cog-whisper-diarization/blob/main/predict.py, without file_url.

    Removed file and file_string.
    """

    group_segments: bool = True
    """Group segments of same speaker shorter apart than 2 seconds"""

    transcript_output_format: Literal["words_only", "segments_only", "both"] = "both"
    """Specify the format of the transcript output: individual words with timestamps, full text of segments, or a combination of both."""

    num_speakers: int | None
    """Number of speakers, leave empty to autodetect."""

    translate: bool = False
    """Translate the speech into English."""

    language: str | None = None
    """Language of the spoken words as a language code like 'en'. Leave empty to auto detect language."""

    prompt: str | None = None
    """Vocabulary: provide names, acronyms and loanwords in a list. Use punctuation for best accuracy."""

    offset_seconds: PositiveInt | None = None
    """Specify the format of the transcript output: individual words with timestamps, full text of segments, or a combination of both."""


class ModelParams(ModelParamsWithoutUrl):
    """Same as ModelParamsWithoutUrl but with the file_url."""

    file_url: HttpUrl
    """Or provide: A direct audio file URL"""
