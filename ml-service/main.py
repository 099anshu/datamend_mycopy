from typing import Dict, Optional, Type

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from detectors.base import AnomalyDetector
from detectors.timercd import TimeRCDDetector
from schemas.analysis import AnalyzeRequest, AnalyzeResponse, Anomaly

app = FastAPI()

_DETECTOR_TYPES: Dict[str, Type[AnomalyDetector]] = {
    "timercd": TimeRCDDetector,
}

detectors: Dict[str, AnomalyDetector] = {}


def _get_detector(name: str) -> AnomalyDetector:
    if name not in _DETECTOR_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown detector: {name}")
    if name not in detectors:
        detectors[name] = _DETECTOR_TYPES[name]()
    return detectors[name]


def _severity(score: float) -> str:
    if score > 0.9:
        return "HIGH"
    if score > 0.6:
        return "MEDIUM"
    return "LOW"


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    if request.detector != "timercd":
        raise HTTPException(status_code=400, detail=f"Unsupported detector: {request.detector}")

    try:
        df = pd.read_csv(request.datasetPath)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {request.datasetPath}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read dataset: {exc}")

    if request.timestampColumn not in df.columns:
        raise HTTPException(status_code=400, detail=f"Missing timestamp column: {request.timestampColumn}")

    missing = [c for c in request.columns if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    data = df[request.columns].to_numpy(dtype=float)
    detector = _get_detector(request.detector)
    scores = detector.detect(data)

    timestamps = df[request.timestampColumn].astype(str).tolist()
    anomalies = []
    for i, score in enumerate(scores):
        for j, col in enumerate(request.columns):
            anomalies.append(
                Anomaly(
                    timestamp=timestamps[i],
                    column=col,
                    value=float(data[i, j]),
                    score=float(score),
                    severity=_severity(float(score)),
                )
            )

    return AnalyzeResponse(
        analysisId=request.analysisId,
        status="COMPLETED",
        detector=request.detector,
        anomalies=anomalies,
    )