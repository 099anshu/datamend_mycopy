from datetime import datetime, timezone
from typing import Dict, List, Type

import pandas as pd
from fastapi import FastAPI, HTTPException

from datasets.tsdb_loader import TsdbLoadError, load_tsdb_dataset
from detectors.base import AnomalyDetector
from detectors.timercd import TimeRCDDetector
from schemas.analysis import (
    AnalysisRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    Anomaly,
    ScoresRequest,
    ScoresResponse,
    TimestampScore,
)

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


def _load_analysis_data(request: AnalysisRequest) -> tuple[pd.DataFrame, object, List[datetime]]:
    try:
        df = load_tsdb_dataset(request.datasetName)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TsdbLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    missing = [column for column in request.columns if column not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")
    if not request.columns:
        raise HTTPException(status_code=400, detail="At least one analysis column is required")

    try:
        data = df[request.columns].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Analysis columns must be numeric: {exc}")

    timestamps = [
        timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
        for timestamp in df.index.to_pydatetime().tolist()
    ]

    scores = _get_detector(request.detector).detect(data)
    if len(scores) != len(df):
        raise HTTPException(status_code=500, detail="Detector returned a score count that does not match the dataset")
    return df, scores, timestamps


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    df, scores, timestamps = _load_analysis_data(request)
    data = df[request.columns].to_numpy(dtype=float)
    anomalies = []
    for i, score in enumerate(scores):
        score = float(score)
        if score < request.threshold:
            continue
        for j, col in enumerate(request.columns):
            anomalies.append(
                Anomaly(
                    timestamp=timestamps[i],
                    column=col,
                    value=float(data[i, j]),
                    score=score,
                    severity=_severity(score),
                )
            )

    return AnalyzeResponse(
        analysisId=request.analysisId,
        status="COMPLETED",
        detector=request.detector,
        anomalies=anomalies,
    )


@app.post("/api/v1/scores", response_model=ScoresResponse)
def scores(request: ScoresRequest) -> ScoresResponse:
    df, detector_scores, timestamps = _load_analysis_data(request)
    series = []
    for i, score in enumerate(detector_scores):
        score = float(score)
        series.append(
            TimestampScore(
                timestamp=timestamps[i],
                values={column: float(df.iloc[i][column]) for column in request.columns},
                score=score,
                severity=_severity(score),
            )
        )

    return ScoresResponse(
        analysisId=request.analysisId,
        status="COMPLETED",
        detector=request.detector,
        scores=series,
    )
