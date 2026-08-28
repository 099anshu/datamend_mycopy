from datetime import datetime, timezone
from typing import Dict, List, Optional, Type

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from corruption.pygrinder import (
    CorruptionConfigError,
    MissingValueHandlingError,
    SUPPORTED_STRATEGIES,
    apply_corruption,
    calc_missing_rate,
    handle_missing_values,
)
from audit.audit_log import AuditEvent, get_audit_trail, record_event
from datasets.loader import load_dataset
from datasets.live_api_loader import LiveApiError, LiveSource, fetch_live_dataset
from datasets.tsdb_loader import TsdbLoadError, list_tsdb_datasets
from datasets.upload_store import (
    UnknownDatasetError,
    UploadError,
    get_metadata,
    list_uploads,
    save_upload,
)
from validation.rule_based import (
    Rule,
    ValidationReport,
    suggest_rules,
    validate_dataset,
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


class LiveFetchRequest(BaseModel):
    source: LiveSource
    # weather params
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pastDays: Optional[int] = None
    # crypto params
    coinId: Optional[str] = None
    vsCurrency: Optional[str] = None
    days: Optional[int] = None


class SuggestRulesRequest(BaseModel):
    datasetId: str
    timestampColumn: Optional[str] = None


class ValidateRequest(BaseModel):
    datasetId: str
    rules: List[Rule]
    timestampColumn: Optional[str] = None

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
        if request.source == "upload":
            record_event(request.datasetName, actor="model", action="corruption_applied",
                         details={"method": request.corruption.method, "missingRate": missing_rate})

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

    if request.source == "upload" and strategy != "reject":
        record_event(request.datasetName, actor="model", action="missing_value_handling",
                     details={"strategy": strategy})

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


@app.post("/api/v1/datasets/live", response_model=UploadedDatasetResponse, status_code=201)
def fetch_live(request: LiveFetchRequest) -> UploadedDatasetResponse:
    """
    Pull a fresh time series from a live public API (weather via Open-Meteo,
    crypto via CoinGecko) and ingest it through the same path as a file
    upload, so it immediately shows up alongside uploaded/TSDB datasets and
    can flow into profiling, rule-based validation, and anomaly detection.
    """
    kwargs = {}
    if request.source == "weather":
        if request.latitude is not None:
            kwargs["latitude"] = request.latitude
        if request.longitude is not None:
            kwargs["longitude"] = request.longitude
        if request.pastDays is not None:
            kwargs["past_days"] = request.pastDays
        filename = "weather_live.csv"
    else:
        if request.coinId is not None:
            kwargs["coin_id"] = request.coinId
        if request.vsCurrency is not None:
            kwargs["vs_currency"] = request.vsCurrency
        if request.days is not None:
            kwargs["days"] = request.days
        filename = f"crypto_{request.coinId or 'bitcoin'}_live.csv"

    try:
        df = fetch_live_dataset(request.source, **kwargs)
    except LiveApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    content = df.to_csv(index=False).encode("utf-8")
    try:
        dataset_id, profile, uploaded_at = save_upload(filename, content, "timestamp")
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_event(dataset_id, actor="user", action="live_fetch",
                 details={"source": request.source, "rowCount": profile.rowCount})

    return UploadedDatasetResponse(
        datasetId=dataset_id, name=filename, uploadedAt=uploaded_at, profile=profile,
    )


@app.post("/api/v1/validate/suggest", response_model=List[Rule])
def suggest_validation_rules(request: SuggestRulesRequest) -> List[Rule]:
    """Auto-detect columns for a dataset and propose default validation rules."""
    try:
        df = load_dataset("upload", request.datasetId, request.timestampColumn)
    except UnknownDatasetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return suggest_rules(df.reset_index().rename(columns={"index": request.timestampColumn or "timestamp"}),
                          timestamp_column=request.timestampColumn or "timestamp")


@app.post("/api/v1/validate", response_model=ValidationReport)
def run_validation(request: ValidateRequest) -> ValidationReport:
    """
    Run rule-based validation (range/not-null/data-type/uniqueness/cross-field
    checks) against a dataset, per Objective #2. Rules can be user-supplied
    or come from /api/v1/validate/suggest.
    """
    try:
        df = load_dataset("upload", request.datasetId, request.timestampColumn)
    except UnknownDatasetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ts_col = request.timestampColumn or "timestamp"
    df = df.reset_index().rename(columns={"index": ts_col})
    report = validate_dataset(df, request.rules, timestamp_column=ts_col)

    record_event(request.datasetId, actor="model", action="rule_validation_run",
                 details={"totalViolations": report.totalViolations,
                          "qualityScore": report.qualityScore,
                          "ruleCount": len(request.rules)})
    return report


@app.get("/api/v1/audit/{dataset_id}", response_model=List[AuditEvent])
def audit_trail(dataset_id: str) -> List[AuditEvent]:
    """Return every recorded change (by user or model) for a dataset."""
    return get_audit_trail(dataset_id)


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
