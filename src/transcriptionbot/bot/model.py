import logging
import time

from faster_whisper import WhisperModel

__logger = logging.getLogger(__name__)


def __get_model():
    """Load the Whisper model."""
    global __model
    __logger.info(f"Loading model...")
    time1 = time.time()
    model = WhisperModel("large-v2", device="cpu", compute_type="int8")
    __logger.info(f"Loaded model in {time.time() - time1:.1f}s")
    return model


model = __get_model()
