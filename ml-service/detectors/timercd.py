from typing import Any, Optional

from time_rcd import TimeRCDDetector as _TimeRCDDetector

from detectors.base import AnomalyDetector


class TimeRCDDetector(AnomalyDetector):
    def __init__(self) -> None:
        self._models: dict[str, Any] = {}

    def detect(self, data: Any) -> Any:
        import numpy as np

        arr = np.asarray(data, dtype=np.float64)
        if arr.ndim == 1:
            variant = "uni"
        else:
            variant = "uni" if arr.shape[1] == 1 else "multi"

        if variant not in self._models:
            self._models[variant] = _TimeRCDDetector.from_pretrained(variant=variant)

        return self._models[variant].predict(arr)