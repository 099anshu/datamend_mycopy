"""Zero-shot TimeRCD anomaly detector for the ml-service.

This wrapper uses TimeRCD strictly as a pretrained, zero-shot anomaly
detector. It is NOT trained or fine-tuned on any target dataset.

Inference path (provided by the packaged ``time_rcd`` library):
``TimeSeriesPretrainModel`` encoder → ``anomaly_head`` → mean over features →
``softmax(...)[..., 1]`` (anomalous-class probability) → per-timestep scores
in ``[0, 1]``. Scoring runs under ``torch.no_grad()`` with ``model.eval()``;
the reconstruction head is never used to produce scores.

Configuration
-------------
``TIMERCD_CHECKPOINT_PATH``:
    Optional path to a local ``.pth`` checkpoint. When set, the detector is
    loaded via ``TimeRCDDetector.from_local`` (raises ``FileNotFoundError`` if
    the path does not exist). When unset, the packaged Hugging Face
    ``from_pretrained`` default is used (repo ``thu-sail-lab/Time-RCD``).
``TIMERCD_WIN_SIZE``:
    Context window length in timesteps (default ``5000``, matching the
    TimeRCD paper's main evaluation setup). Sequences shorter than the window
    use their full length.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from time_rcd import TimeRCDDetector as _TimeRCDDetector

from detectors.base import AnomalyDetector

DEFAULT_WIN_SIZE = 5000

_ENV_CHECKPOINT_PATH = "TIMERCD_CHECKPOINT_PATH"
_ENV_WIN_SIZE = "TIMERCD_WIN_SIZE"


def _env_win_size() -> int:
    raw = os.environ.get(_ENV_WIN_SIZE)
    if raw is None:
        return DEFAULT_WIN_SIZE
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"{_ENV_WIN_SIZE} must be an integer, got {raw!r}"
        ) from None
    if value < 1:
        raise ValueError(f"{_ENV_WIN_SIZE} must be >= 1, got {value}")
    return value


class TimeRCDDetector(AnomalyDetector):
    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._checkpoint_path = os.environ.get(_ENV_CHECKPOINT_PATH)
        self._win_size = _env_win_size()

    def _load_model(self, variant: str) -> _TimeRCDDetector:
        kwargs: dict[str, Any] = {"variant": variant, "win_size": self._win_size}
        if self._checkpoint_path is None:
            return _TimeRCDDetector.from_pretrained(**kwargs)
        path = Path(self._checkpoint_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"{_ENV_CHECKPOINT_PATH} is set to {self._checkpoint_path!r} "
                f"but that file does not exist."
            )
        return _TimeRCDDetector.from_local(path, **kwargs)

    def detect(self, data: Any, return_logits: bool = False) -> Any:
        import numpy as np

        arr = np.asarray(data, dtype=np.float64)
        if arr.ndim == 1:
            variant = "uni"
        else:
            variant = "uni" if arr.shape[1] == 1 else "multi"

        if variant not in self._models:
            self._models[variant] = self._load_model(variant)

        return self._models[variant].predict(arr, return_logits=return_logits)
