from functools import lru_cache
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

_ETT_SUBDATASETS = {"ETTh1", "ETTh2", "ETTm1", "ETTm2"}
_ETT_SOURCE = "electricity_transformer_temperature"


class TsdbLoadError(RuntimeError):
    """Raised when TSDB cannot provide a requested dataset."""


def list_tsdb_datasets() -> List[str]:
    """List all available datasets in TSDB plus convenience aliases."""
    try:
        import tsdb
        raw_list = tsdb.list()
    except Exception as exc:
        raw_list = []

    result = list(_ETT_SUBDATASETS)
    for name in raw_list:
        if name not in result:
            result.append(name)
    return result


def list_tsdb_cache() -> List[str]:
    """List all datasets currently cached by TSDB."""
    try:
        import tsdb
        return tsdb.list_cache()
    except Exception as exc:
        raise TsdbLoadError(f"Failed to list TSDB cache: {exc}") from exc


def delete_tsdb_cache(dataset_name: Optional[str] = None, only_pickle: bool = False) -> None:
    """Delete all or specific TSDB dataset cache."""
    try:
        import tsdb
        if dataset_name:
            tsdb.delete_cache(dataset_name=dataset_name, only_pickle=only_pickle)
        else:
            tsdb.delete_cache()
    except Exception as exc:
        raise TsdbLoadError(f"Failed to delete TSDB cache: {exc}") from exc


def download_and_extract_tsdb(dataset_name: str, save_path: str) -> None:
    """Download and extract raw dataset files to target directory."""
    try:
        import tsdb
        tsdb.download_and_extract(dataset_name, save_path)
    except Exception as exc:
        raise TsdbLoadError(f"Failed to download/extract TSDB dataset {dataset_name!r}: {exc}") from exc


def migrate_tsdb_cache(target_path: str) -> None:
    """Migrate the TSDB cache directory to a new location."""
    try:
        import tsdb
        tsdb.migrate_cache(target_path)
    except Exception as exc:
        raise TsdbLoadError(f"Failed to migrate TSDB cache: {exc}") from exc


def _normalize_to_dataframe(data: Any, dataset_name: str) -> pd.DataFrame:
    """Convert any TSDB data return type into a DataFrame with DatetimeIndex."""
    df: Optional[pd.DataFrame] = None

    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, dict):
        # Multi-table or split dictionary
        if dataset_name in data and isinstance(data[dataset_name], pd.DataFrame):
            df = data[dataset_name].copy()
        elif "X" in data:
            x_data = data["X"]
            if isinstance(x_data, pd.DataFrame):
                df = x_data.copy()
            elif isinstance(x_data, np.ndarray):
                if x_data.ndim == 3:
                    # [samples, timesteps, features] -> flatten or take first instance/flatten
                    s, t, f = x_data.shape
                    reshaped = x_data.reshape(-1, f)
                    df = pd.DataFrame(reshaped, columns=[f"dim_{i}" for i in range(f)])
                elif x_data.ndim == 2:
                    df = pd.DataFrame(x_data, columns=[f"dim_{i}" for i in range(x_data.shape[1])])
                elif x_data.ndim == 1:
                    df = pd.DataFrame(x_data, columns=["value"])
        elif "train" in data and isinstance(data["train"], (pd.DataFrame, np.ndarray)):
            return _normalize_to_dataframe(data["train"], dataset_name)
        elif "data" in data and isinstance(data["data"], (pd.DataFrame, np.ndarray)):
            return _normalize_to_dataframe(data["data"], dataset_name)
        else:
            # Pick first DataFrame found in dict
            for k, v in data.items():
                if isinstance(v, pd.DataFrame):
                    df = v.copy()
                    break
            if df is None:
                # Convert any array in dict to DataFrame
                for k, v in data.items():
                    if isinstance(v, np.ndarray) and v.ndim in (1, 2):
                        df = pd.DataFrame(v)
                        break

    elif isinstance(data, np.ndarray):
        if data.ndim == 2:
            df = pd.DataFrame(data, columns=[f"dim_{i}" for i in range(data.shape[1])])
        elif data.ndim == 1:
            df = pd.DataFrame(data, columns=["value"])

    if df is None:
        raise TsdbLoadError(
            f"Could not convert TSDB dataset {dataset_name!r} (type {type(data).__name__}) to pandas DataFrame"
        )

    # Ensure column names are strings
    df.columns = [str(c) for c in df.columns]

    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        # Look for existing timestamp/datetime column
        timestamp_col = None
        for candidate in ["date", "time", "timestamp", "datetime", "Date", "Time", "Timestamp", "DateTime"]:
            if candidate in df.columns:
                timestamp_col = candidate
                break

        if timestamp_col is not None:
            try:
                df.index = pd.to_datetime(df[timestamp_col], utc=True)
                df = df.drop(columns=[timestamp_col])
            except Exception:
                df.index = pd.date_range("2020-01-01", periods=len(df), freq="h", tz="UTC")
        else:
            df.index = pd.date_range("2020-01-01", periods=len(df), freq="h", tz="UTC")

    # Drop any remaining non-numeric columns
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        # Try coercing object columns to float
        coerced = df.apply(pd.to_numeric, errors="coerce").dropna(how="all", axis=1)
        if not coerced.empty:
            numeric_df = coerced

    if numeric_df.empty:
        raise TsdbLoadError(f"TSDB dataset {dataset_name!r} contains no numeric signal columns")

    return numeric_df


@lru_cache(maxsize=16)
def _load_tsdb_raw(source_name: str) -> Any:
    try:
        import tsdb
        return tsdb.load(source_name)
    except Exception as exc:
        raise TsdbLoadError(f"Failed to load TSDB source {source_name!r}: {exc}") from exc


def load_tsdb_dataset(dataset_name: str) -> pd.DataFrame:
    """Load any dataset from TSDB as a DatetimeIndex-ed DataFrame.
    
    Supports:
    - Standard TSDB dataset names (e.g. 'physionet_2012', 'beijing_multisite_air_quality', 'italy_air_quality')
    - ETT split shortcuts ('ETTh1', 'ETTh2', 'ETTm1', 'ETTm2')
    - Sub-split notation ('electricity_transformer_temperature/ETTh1')
    """
    clean_name = dataset_name.strip()

    if clean_name in _ETT_SUBDATASETS:
        raw = _load_tsdb_raw(_ETT_SOURCE)
        if isinstance(raw, dict) and clean_name in raw:
            return _normalize_to_dataframe(raw[clean_name], clean_name)
        return _normalize_to_dataframe(raw, clean_name)

    if "/" in clean_name:
        source_part, sub_part = clean_name.split("/", 1)
        raw = _load_tsdb_raw(source_part)
        if isinstance(raw, dict) and sub_part in raw:
            return _normalize_to_dataframe(raw[sub_part], sub_part)
        return _normalize_to_dataframe(raw, sub_part)

    raw = _load_tsdb_raw(clean_name)
    return _normalize_to_dataframe(raw, clean_name)
