from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter

from transcription_bot.transcribers.replicate.base import ReplicateTranscriberBase


class ParamsWithoutUrl(BaseModel):
    """From https://github.com/chenxwh/insanely-fast-whisper/blob/main/predict.py."""

    task: Literal["transcribe", "translate"] = "transcribe"
    """Task to perform: transcribe or translate to another language."""

    language: str = "english"

    batch_size: int = 24
    """Number of parallel batches you want to compute. Reduce if you face OOMs."""

    timestamp: Literal["chunk", "word"] = "chunk"

    diarise_audio: bool = True

    hf_token: str


class Params(ParamsWithoutUrl):
    """Paramemeters with audio url included."""

    audio: str


class Output(BaseModel):
    """Output format for the insanely fast whisper model."""

    speaker: str
    text: str
    timestamp: list[float]


class InsanelyFastWhisper(ReplicateTranscriberBase):
    """Uses vaibhavs10/incredibly-fast-whisper."""

    def __init__(self, version: str, params: ParamsWithoutUrl) -> None:
        """Prepare a prediction pipeline."""
        self.params = params
        super().__init__(version)

    def _get_model_name(self) -> str:
        return "vaibhavs10/incredibly-fast-whisper"

    def _get_model_params(self, file_url: str) -> dict[str, Any]:
        params_with_url = Params(**self.params.model_dump(), audio=file_url)
        return params_with_url.model_dump(exclude_none=True)

    def _process_output(self, model_output: Any) -> str:
        output_adapter = TypeAdapter(list[Output])
        segments = output_adapter.validate_python(model_output[:-1])

        # Merge speakers

        current_group = {
            "start": segments[0].timestamp[0],
            "end": segments[0].timestamp[1],
            "speaker": segments[0].speaker,
            "text": segments[0].text,
        }
        diarization_output = []

        max_gap_between_segments = 2

        for i in range(1, len(segments)):
            # Calculate time gap between consecutive segments
            time_gap = segments[i].timestamp[0] - segments[i - 1].timestamp[1]

            # If the current segment's speaker is the same as the previous segment's speaker,
            # and the time gap is less than or equal to 2 seconds, group them
            if (
                segments[i].speaker == segments[i - 1].speaker
                and time_gap < max_gap_between_segments
            ):
                current_group["end"] = segments[i].timestamp[1]
                current_group["text"] += " " + segments[i].text
            else:
                # Add the current_group to the output list
                diarization_output.append(current_group)

                # Start a new group with the current segment
                current_group = {
                    "start": segments[i].timestamp[0],
                    "end": segments[i].timestamp[1],
                    "speaker": segments[i].speaker,
                    "text": segments[i].text,
                }
        diarization_output.append(current_group)

        return "\n\n".join([f"{s["speaker"]}: {s["text"]}" for s in diarization_output])
