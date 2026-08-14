from typing import List, Literal

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    analysisId: str
    datasetPath: str
    timestampColumn: str
    columns: List[str]
    detector: str


class Anomaly(BaseModel):
    timestamp: str
    column: str
    value: float
    score: float
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class AnalyzeResponse(BaseModel):
    analysisId: str
    status: Literal["COMPLETED"]
    detector: str
    anomalies: List[Anomaly]