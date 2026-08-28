from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from schemas.dataset import DatasetSource


class CorruptionRequest(BaseModel):
    enabled: bool
    method: str
    params: Dict[str, Any] = {}


class MissingValueHandling(BaseModel):
    strategy: str = "reject"


class AnalysisRequest(BaseModel):
    analysisId: str
    datasetName: str
    columns: List[str]
    detector: str
    source: DatasetSource = "tsdb"
    timestampColumn: Optional[str] = None
    corruption: Optional[CorruptionRequest] = None
    missingValueHandling: Optional[MissingValueHandling] = None


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
    missingRate: Optional[float] = None
    missingValueHandling: Optional[str] = None


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
    missingRate: Optional[float] = None
    missingValueHandling: Optional[str] = None
