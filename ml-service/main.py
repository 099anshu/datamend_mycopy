from datetime import datetime, timezone
from typing import Dict, List, Optional, Type

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from corruption.pygrinder import (
    CorruptionConfigError,
    MissingValueHandlingError,
    SUPPORTED_STRATEGIES,
    apply_corruption,
    calc_missing_rate,
    handle_missing_values,
)
from datasets.loader import load_dataset
from datasets.tsdb_loader import TsdbLoadError, list_tsdb_datasets
from datasets.upload_store import (
    UnknownDatasetError,
    UploadError,
    get_metadata,
    list_uploads,
    save_upload,
)
from datasets.ts_analysis import (
    calculate_rolling_statistics,
    calculate_differences,
    scale_time_series,
    create_interactive_data_structure,
)
from detectors.base import AnomalyDetector
from detectors.timercd import TimeRCDDetector
from schemas.dataset import (
    DatasetProfile,
    UploadedDatasetResponse,
    UploadedDatasetSummary,
)
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


def _load_analysis_data(
    request: AnalysisRequest,
) -> tuple[pd.DataFrame, object, List[datetime], Optional[float], str]:
    try:
        df = load_dataset(request.source, request.datasetName, request.timestampColumn)
    except UnknownDatasetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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

    missing_rate = None
    data_with_nans = data
    if request.corruption is not None and request.corruption.enabled:
        try:
            data_with_nans = apply_corruption(
                data, request.corruption.method, request.corruption.params
            )
            missing_rate = calc_missing_rate(data_with_nans)
        except CorruptionConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    strategy = "reject"
    if request.missingValueHandling is not None:
        strategy = request.missingValueHandling.strategy
    if strategy not in SUPPORTED_STRATEGIES:
        supported = ", ".join(sorted(SUPPORTED_STRATEGIES))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown missing-value handling strategy {strategy!r}. "
            f"Supported strategies: {supported}",
        )

    try:
        detector_input = handle_missing_values(data_with_nans, strategy)
    except MissingValueHandlingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scores = _get_detector(request.detector).detect(detector_input)
    if len(scores) != len(df):
        raise HTTPException(status_code=500, detail="Detector returned a score count that does not match the dataset")
    return df, scores, timestamps, missing_rate, strategy


@app.post("/api/v1/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    df, scores, timestamps, missing_rate, strategy = _load_analysis_data(request)
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
        missingRate=missing_rate,
        missingValueHandling=strategy,
    )


@app.post("/api/v1/scores", response_model=ScoresResponse, response_model_exclude_none=True)
def scores(request: ScoresRequest) -> ScoresResponse:
    df, detector_scores, timestamps, missing_rate, strategy = _load_analysis_data(request)
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
        missingRate=missing_rate,
        missingValueHandling=strategy,
    )


@app.get("/api/v1/datasets", response_model=List[UploadedDatasetSummary])
def list_datasets() -> List[UploadedDatasetSummary]:
    return list_uploads()


@app.get("/api/v1/datasets/sources/tsdb", response_model=List[str])
def list_tsdb_sources() -> List[str]:
    return list_tsdb_datasets()


@app.post("/api/v1/datasets", response_model=UploadedDatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    timestampColumn: Optional[str] = Form(default=None),
) -> UploadedDatasetResponse:
    content = await file.read()
    try:
        dataset_id, profile, uploaded_at = save_upload(
            file.filename or "dataset.csv", content, timestampColumn
        )
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadedDatasetResponse(
        datasetId=dataset_id,
        name=file.filename or "dataset.csv",
        uploadedAt=uploaded_at,
        profile=profile,
    )


@app.get("/api/v1/datasets/{dataset_id}", response_model=UploadedDatasetResponse)
def get_dataset(dataset_id: str) -> UploadedDatasetResponse:
    try:
        metadata = get_metadata(dataset_id)
    except UnknownDatasetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return UploadedDatasetResponse(
        datasetId=metadata["datasetId"],
        name=metadata["name"],
        uploadedAt=datetime.fromisoformat(metadata["uploadedAt"]),
        profile=DatasetProfile.model_validate(metadata["profile"]),
    )


@app.post("/api/v1/analysis/rolling")
def calculate_rolling(
    source: str = Form(...),
    datasetName: str = Form(...),
    columns: List[str] = Form(...),
    window: int = Form(default=24),
    timestampColumn: Optional[str] = Form(default=None),
) -> Dict:
    """Calculate rolling statistics for time series data."""
    try:
        df = load_dataset(source, datasetName, timestampColumn)
    except (UnknownDatasetError, ValueError, TsdbLoadError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    result_df = calculate_rolling_statistics(df, window=window, columns=columns)
    
    # Convert to interactive format
    interactive_data = create_interactive_data_structure(result_df, columns)
    
    return {
        "status": "success",
        "window": window,
        "data": interactive_data,
        "columns": columns,
    }


@app.post("/api/v1/analysis/differences")
def calculate_diff(
    source: str = Form(...),
    datasetName: str = Form(...),
    columns: List[str] = Form(...),
    periods: int = Form(default=1),
    timestampColumn: Optional[str] = Form(default=None),
) -> Dict:
    """Calculate differences for time series data."""
    try:
        df = load_dataset(source, datasetName, timestampColumn)
    except (UnknownDatasetError, ValueError, TsdbLoadError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    result_df = calculate_differences(df, columns=columns, periods=periods)
    
    # Convert to interactive format
    interactive_data = create_interactive_data_structure(result_df, columns)
    
    return {
        "status": "success",
        "periods": periods,
        "data": interactive_data,
        "columns": columns,
    }


@app.post("/api/v1/analysis/scale")
def scale_data(
    source: str = Form(...),
    datasetName: str = Form(...),
    columns: List[str] = Form(...),
    method: str = Form(default="standard"),
    timestampColumn: Optional[str] = Form(default=None),
) -> Dict:
    """Scale time series data using various methods."""
    try:
        df = load_dataset(source, datasetName, timestampColumn)
    except (UnknownDatasetError, ValueError, TsdbLoadError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    if method not in ["standard", "minmax", "robust"]:
        raise HTTPException(status_code=400, detail="Invalid scaling method. Use: standard, minmax, or robust")

    result_df = scale_time_series(df, columns=columns, method=method)
    
    # Convert to interactive format
    scaled_columns = [f"{col}_scaled" for col in columns]
    interactive_data = create_interactive_data_structure(result_df, scaled_columns)
    
    return {
        "status": "success",
        "method": method,
        "data": interactive_data,
        "columns": scaled_columns,
    }
