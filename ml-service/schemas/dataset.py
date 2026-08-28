from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel

DatasetSource = Literal["tsdb", "upload"]

ColumnKind = Literal["numeric", "datetime", "categorical"]


class ColumnProfile(BaseModel):
    name: str
    kind: ColumnKind
    dtype: str
    nullCount: int
    nullRate: float
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    sampleValues: List[str] = []


class DatasetProfile(BaseModel):
    rowCount: int
    columnCount: int
    timestampColumn: Optional[str] = None
    signalColumns: List[str] = []
    columns: List[ColumnProfile] = []
    preview: List[dict[str, Any]] = []


class UploadedDatasetResponse(BaseModel):
    datasetId: str
    name: str
    source: DatasetSource = "upload"
    uploadedAt: datetime
    profile: DatasetProfile


class UploadedDatasetSummary(BaseModel):
    datasetId: str
    name: str
    source: DatasetSource = "upload"
    uploadedAt: datetime
    rowCount: int
    columnCount: int
