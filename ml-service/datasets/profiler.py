"""Schema inference and statistical profiling for user-supplied datasets."""

from typing import List, Optional

import numpy as np
import pandas as pd

from schemas.dataset import ColumnKind, ColumnProfile, DatasetProfile

PREVIEW_ROWS = 20
SAMPLE_VALUES = 3

_TIMESTAMP_NAME_HINTS = ("timestamp", "time", "date", "datetime", "ts")
_MIN_PARSE_RATE = 0.9


def _is_datetime_like(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if not pd.api.types.is_object_dtype(series) and not pd.api.types.is_string_dtype(series):
        return False
    sample = series.dropna().head(200)
    if sample.empty:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return parsed.notna().mean() >= _MIN_PARSE_RATE


def detect_timestamp_column(df: pd.DataFrame) -> Optional[str]:
    """Pick the column most likely to hold the time axis.

    Name hints win over positional heuristics; otherwise the first
    datetime-parseable column is used.
    """
    candidates = [column for column in df.columns if _is_datetime_like(df[column])]
    if not candidates:
        return None
    for column in candidates:
        if str(column).strip().lower() in _TIMESTAMP_NAME_HINTS:
            return column
    for column in candidates:
        if any(hint in str(column).strip().lower() for hint in _TIMESTAMP_NAME_HINTS):
            return column
    return candidates[0]


def _column_kind(series: pd.Series, is_timestamp: bool) -> ColumnKind:
    if is_timestamp:
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "categorical"


def _finite(value: float) -> Optional[float]:
    if value is None or not np.isfinite(value):
        return None
    return float(value)


def _profile_column(series: pd.Series, is_timestamp: bool) -> ColumnProfile:
    kind = _column_kind(series, is_timestamp)
    row_count = len(series)
    null_count = int(series.isna().sum())
    profile = ColumnProfile(
        name=str(series.name),
        kind=kind,
        dtype=str(series.dtype),
        nullCount=null_count,
        nullRate=round(null_count / row_count, 6) if row_count else 0.0,
        sampleValues=[str(value) for value in series.dropna().head(SAMPLE_VALUES).tolist()],
    )
    if kind == "numeric":
        profile.min = _finite(series.min())
        profile.max = _finite(series.max())
        profile.mean = _finite(series.mean())
        profile.std = _finite(series.std())
    return profile


def profile_dataframe(df: pd.DataFrame, timestamp_column: Optional[str] = None) -> DatasetProfile:
    """Describe a raw uploaded frame: column kinds, missingness, ranges, preview rows."""
    if timestamp_column is None:
        timestamp_column = detect_timestamp_column(df)

    columns = [_profile_column(df[column], column == timestamp_column) for column in df.columns]
    signal_columns: List[str] = [column.name for column in columns if column.kind == "numeric"]

    preview = df.head(PREVIEW_ROWS).astype(object).where(pd.notna(df.head(PREVIEW_ROWS)), None)
    preview_records = [
        {str(key): (str(value) if isinstance(value, pd.Timestamp) else value) for key, value in record.items()}
        for record in preview.to_dict(orient="records")
    ]

    return DatasetProfile(
        rowCount=int(len(df)),
        columnCount=int(len(df.columns)),
        timestampColumn=str(timestamp_column) if timestamp_column is not None else None,
        signalColumns=signal_columns,
        columns=columns,
        preview=preview_records,
    )
