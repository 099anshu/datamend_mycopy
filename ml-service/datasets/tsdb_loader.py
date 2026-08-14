from functools import lru_cache

import pandas as pd

_TSDB_SOURCE = "electricity_transformer_temperature"
_SUPPORTED_DATASETS = ("ETTh1", "ETTh2", "ETTm1", "ETTm2")


class TsdbLoadError(RuntimeError):
    """Raised when TSDB cannot provide a requested dataset."""


def list_tsdb_datasets() -> list[str]:
    return list(_SUPPORTED_DATASETS)


@lru_cache(maxsize=1)
def _load_electricity_transformer_temperature() -> dict[str, pd.DataFrame]:
    try:
        import tsdb

        data = tsdb.load(_TSDB_SOURCE)
    except Exception as exc:
        raise TsdbLoadError(
            f"Failed to load TSDB source {_TSDB_SOURCE!r}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise TsdbLoadError(
            f"TSDB source {_TSDB_SOURCE!r} returned {type(data).__name__}, expected a dictionary"
        )
    return data


def load_tsdb_dataset(dataset_name: str) -> pd.DataFrame:
    """Load one supported ETT split directly from TSDB as a DataFrame."""
    if dataset_name not in _SUPPORTED_DATASETS:
        supported = ", ".join(_SUPPORTED_DATASETS)
        raise ValueError(f"Unknown TSDB dataset {dataset_name!r}. Supported datasets: {supported}")

    data = _load_electricity_transformer_temperature()
    try:
        dataset = data[dataset_name]
    except KeyError as exc:
        raise TsdbLoadError(
            f"TSDB source {_TSDB_SOURCE!r} did not contain dataset {dataset_name!r}"
        ) from exc

    if not isinstance(dataset, pd.DataFrame):
        raise TsdbLoadError(
            f"TSDB dataset {dataset_name!r} is {type(dataset).__name__}, expected a pandas DataFrame"
        )
    if not isinstance(dataset.index, pd.DatetimeIndex):
        raise TsdbLoadError(f"TSDB dataset {dataset_name!r} does not have a DatetimeIndex")
    return dataset
