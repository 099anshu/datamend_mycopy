"""Source-agnostic dataset resolution for analysis requests."""

from typing import Optional

import pandas as pd

from datasets.tsdb_loader import load_tsdb_dataset
from datasets.upload_store import load_uploaded_dataset


def load_dataset(
    source: str,
    dataset_name: str,
    timestamp_column: Optional[str] = None,
) -> pd.DataFrame:
    """Resolve a dataset from its source into a DatetimeIndex-ed frame.

    For ``upload``, ``dataset_name`` is the stored dataset id.
    """
    if source == "tsdb":
        return load_tsdb_dataset(dataset_name)
    if source == "upload":
        return load_uploaded_dataset(dataset_name, timestamp_column)
    raise ValueError(f"Unknown dataset source {source!r}. Supported sources: tsdb, upload")
