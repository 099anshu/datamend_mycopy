from abc import ABC, abstractmethod
from typing import Any


class AnomalyDetector(ABC):
    @abstractmethod
    def detect(self, data: Any) -> Any:
        raise NotImplementedError