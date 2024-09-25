from typing import Literal

type PredictionStatus = Literal[
    "starting",
    "processing",
    "succeeded",
    "failed",
    "canceled",
]
