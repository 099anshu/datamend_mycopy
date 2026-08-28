"""Filesystem-backed store for user-uploaded time-series datasets."""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd

from datasets.profiler import profile_dataframe
from datasets.ts_parser import parse_ts_file, convert_ts_to_dataframe, TSParseError
from schemas.dataset import DatasetProfile, UploadedDatasetSummary

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
SUPPORTED_EXTENSIONS = (".csv", ".tsv", ".txt", ".ts")

_DATASET_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class UploadError(ValueError):
    """Raised when an uploaded file cannot be accepted."""


class UnknownDatasetError(LookupError):
    """Raised when a dataset id does not resolve to a stored upload."""


def upload_dir() -> Path:
    """Storage root, overridable so tests and deployments can relocate uploads."""
    path = Path(os.environ.get("DATAMEND_UPLOAD_DIR", "data/uploads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _paths(dataset_id: str) -> tuple[Path, Path]:
    if not _DATASET_ID_PATTERN.match(dataset_id):
        raise UnknownDatasetError(f"Invalid dataset id: {dataset_id!r}")
    root = upload_dir()
    return root / f"{dataset_id}.csv", root / f"{dataset_id}.json"


def _read_csv(content: bytes, separator: str) -> pd.DataFrame:
    from io import BytesIO

    try:
        df = pd.read_csv(BytesIO(content), sep=separator)
    except UnicodeDecodeError as exc:
        raise UploadError(f"File is not valid UTF-8 text: {exc}") from exc
    except pd.errors.ParserError as exc:
        raise UploadError(f"Could not parse file as delimited text: {exc}") from exc
    except pd.errors.EmptyDataError as exc:
        raise UploadError("File is empty") from exc

    if df.empty:
        raise UploadError("File contains no data rows")
    if len(df.columns) < 2:
        raise UploadError(
            "Dataset needs at least two columns: a timestamp column and one signal column"
        )
    return df


def _read_ts(content: bytes) -> pd.DataFrame:
    """Read and parse a .ts file in UCR/UEA format."""
    try:
        df, metadata = parse_ts_file(content)
        # Convert to standard time series format
        df = convert_ts_to_dataframe(df, metadata)
    except TSParseError as exc:
        raise UploadError(f"Could not parse .ts file: {exc}") from exc
    
    if df.empty:
        raise UploadError("File contains no data rows")
    if len(df.columns) < 1:
        raise UploadError(
            "Dataset needs at least one signal column"
        )
    return df


def save_upload(filename: str, content: bytes, timestamp_column: Optional[str] = None) -> tuple[str, DatasetProfile, datetime]:
    """Persist an uploaded file and return its id, profile and upload time."""
    if not content:
        raise UploadError("File is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError(
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit"
        )

    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_EXTENSIONS)
        raise UploadError(f"Unsupported file type {suffix or '(none)'!r}. Supported: {supported}")

    if suffix == ".ts":
        df = _read_ts(content)
        # For .ts files, timestamp is auto-generated, so timestamp_column is not needed
        timestamp_column = None
        is_ts_file = True
    else:
        df = _read_csv(content, separator="\t" if suffix == ".tsv" else ",")
        if timestamp_column is not None and timestamp_column not in df.columns:
            raise UploadError(f"Timestamp column {timestamp_column!r} is not present in the file")
        is_ts_file = False

    profile = profile_dataframe(df, timestamp_column, is_ts_file=is_ts_file)
    dataset_id = uuid.uuid4().hex
    uploaded_at = datetime.now(timezone.utc)
    data_path, meta_path = _paths(dataset_id)

    # For .ts files, we need to save with the timestamp index since it's auto-generated
    if suffix == ".ts":
        df.to_csv(data_path, index=True)
        is_ts_file = True
    else:
        df.to_csv(data_path, index=False)
        is_ts_file = False
    
    meta_path.write_text(
        json.dumps(
            {
                "datasetId": dataset_id,
                "name": Path(filename).name,
                "uploadedAt": uploaded_at.isoformat(),
                "profile": profile.model_dump(mode="json"),
                "isTsFile": is_ts_file,
            }
        ),
        encoding="utf-8",
    )
    return dataset_id, profile, uploaded_at


def _read_metadata(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UnknownDatasetError(f"Unknown dataset: {meta_path.stem}") from exc


def get_metadata(dataset_id: str) -> dict:
    _, meta_path = _paths(dataset_id)
    return _read_metadata(meta_path)


def list_uploads() -> List[UploadedDatasetSummary]:
    summaries = []
    for meta_path in sorted(upload_dir().glob("*.json")):
        metadata = _read_metadata(meta_path)
        profile = metadata["profile"]
        summaries.append(
            UploadedDatasetSummary(
                datasetId=metadata["datasetId"],
                name=metadata["name"],
                uploadedAt=datetime.fromisoformat(metadata["uploadedAt"]),
                rowCount=profile["rowCount"],
                columnCount=profile["columnCount"],
            )
        )
    return sorted(summaries, key=lambda summary: summary.uploadedAt, reverse=True)


def load_uploaded_dataset(dataset_id: str, timestamp_column: Optional[str] = None) -> pd.DataFrame:
    """Load a stored upload indexed by its timestamp column."""
    data_path, meta_path = _paths(dataset_id)
    metadata = _read_metadata(meta_path)
    if not data_path.exists():
        raise UnknownDatasetError(f"Dataset {dataset_id} has metadata but no stored file")

    # Check if this was a .ts file using the metadata flag
    is_ts_file = metadata.get("isTsFile", False)
    
    if is_ts_file:
        # .ts files were saved with index
        df = pd.read_csv(data_path, index_col=0)
        df.index = pd.to_datetime(df.index, errors="coerce")
        if df.index.isna().any():
            raise UploadError("Timestamp index contains invalid values")
        df.index = pd.DatetimeIndex(df.index)
    else:
        # Regular CSV files
        df = pd.read_csv(data_path)
        resolved = timestamp_column or metadata["profile"].get("timestampColumn")
        if resolved is None:
            raise UploadError(
                "No timestamp column is set for this dataset. Choose one before running analysis."
            )
        if resolved not in df.columns:
            raise UploadError(f"Timestamp column {resolved!r} is not present in the dataset")

        index = pd.to_datetime(df[resolved], errors="coerce", format="mixed")
        if index.isna().any():
            raise UploadError(f"Column {resolved!r} contains values that are not valid timestamps")

        df = df.drop(columns=[resolved])
        df.index = pd.DatetimeIndex(index)
    
    return df.sort_index()
