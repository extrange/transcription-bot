from typing import Any

from pydantic import BaseModel

from transcription_bot.transcribers.replicate.base import ReplicateTranscriberBase


class Word(BaseModel):
    """Information about a single word from a segment."""

    end: float
    probability: float
    start: float
    word: str


class Segment(BaseModel):
    """Contains speaker information."""

    avg_logprob: float | None = None
    end: float
    speaker: str
    start: float
    text: str
    words: list[Word] = []


class Output(BaseModel):
    """Output from thomasmol/whisper-diarization."""

    language: str | None = None
    num_speakers: int | None = None
    segments: list[Segment]


class ThomasmolParamsWithoutUrl(BaseModel):
    """
    Parameters as from https://github.com/thomasmol/cog-whisper-diarization/blob/main/predict.py, without file_url.

    Sane defaults set.

    Removed file and file_string, and the inputs that newer versions no longer
    accept (`group_segments`, `transcript_output_format`, `offset_seconds`).
    """

    num_speakers: int | None = None
    """Number of speakers, leave empty to autodetect."""

    translate: bool = False
    """Translate the speech into English."""

    language: str | None = "en"
    """Language of the spoken words as a language code like 'en'. Leave empty to auto detect language."""

    prompt: str | None = "Hello."
    """Vocabulary: provide names, acronyms and loanwords in a list. Use punctuation for best accuracy."""


class ThomasmolParams(ThomasmolParamsWithoutUrl):
    """Same as ModelParamsWithoutUrl but with the file_url."""

    file_url: str
    """Or provide: A direct audio file URL"""


class ThomasmolTranscriber(ReplicateTranscriberBase):
    """Uses thomasmol/whisper-diarization, on its latest version unless pinned."""

    def __init__(self, version: str | None, params: ThomasmolParamsWithoutUrl) -> None:
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
