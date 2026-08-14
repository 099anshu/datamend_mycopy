from datetime import datetime
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    analysisId: str
    datasetName: str
    columns: List[str]
    detector: str


class AnalyzeRequest(AnalysisRequest):
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class ScoresRequest(AnalysisRequest):
    pass


class Anomaly(BaseModel):
    timestamp: datetime
    column: str
    value: float
    score: float
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class AnalyzeResponse(BaseModel):
    analysisId: str
    status: Literal["COMPLETED"]
    detector: str
    anomalies: List[Anomaly]


class TimestampScore(BaseModel):
    timestamp: datetime
    values: Dict[str, float]
    score: float
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class ScoresResponse(BaseModel):
    analysisId: str
    status: Literal["COMPLETED"]
    detector: str
    scores: List[TimestampScore]
