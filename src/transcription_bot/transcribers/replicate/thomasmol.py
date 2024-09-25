from typing import Any, Literal

from pydantic import BaseModel, PositiveInt

from transcription_bot.transcribers.replicate.base import ReplicateTranscriberBase


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


class ThomasmolParamsWithoutUrl(BaseModel):
    """
    Parameters as from https://github.com/thomasmol/cog-whisper-diarization/blob/main/predict.py, without file_url.

    Sane defaults set.

    Removed file and file_string.
    """

    group_segments: bool = True
    """Group segments of same speaker shorter apart than 2 seconds"""

    transcript_output_format: Literal["words_only", "segments_only", "both"] = "both"
    """Specify the format of the transcript output: individual words with timestamps, full text of segments, or a combination of both."""

    num_speakers: int | None = None
    """Number of speakers, leave empty to autodetect."""

    translate: bool = False
    """Translate the speech into English."""

    language: str | None = "en"
    """Language of the spoken words as a language code like 'en'. Leave empty to auto detect language."""

    prompt: str | None = "Hello."
    """Vocabulary: provide names, acronyms and loanwords in a list. Use punctuation for best accuracy."""

    offset_seconds: PositiveInt | None = None
    """Specify the format of the transcript output: individual words with timestamps, full text of segments, or a combination of both."""


class ThomasmolParams(ThomasmolParamsWithoutUrl):
    """Same as ModelParamsWithoutUrl but with the file_url."""

    file_url: str
    """Or provide: A direct audio file URL"""


class ThomasmolTranscriber(ReplicateTranscriberBase):
    """Uses thomasmol/whisper-diarization."""

    def __init__(self, version: str, params: ThomasmolParamsWithoutUrl) -> None:
        """Prepare a prediction pipeline."""
        self.params = params
        super().__init__(version)

    def _get_model_name(self) -> str:
        return "thomasmol/whisper-diarization"

    def _get_model_params(self, file_url: str) -> dict[str, Any]:
        params_with_url = ThomasmolParams(**self.params.model_dump(), file_url=file_url)
        return params_with_url.model_dump(exclude_none=True)

    def _process_output(self, model_output: Any) -> str:
        output = Output.model_validate(model_output)
        return "\n\n".join([f"{s.speaker}: {s.text}" for s in output.segments])
