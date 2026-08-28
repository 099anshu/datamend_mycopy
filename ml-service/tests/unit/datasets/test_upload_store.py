import pandas as pd
import pytest

from datasets.profiler import detect_timestamp_column, profile_dataframe
from datasets.upload_store import (
    UnknownDatasetError,
    UploadError,
    list_uploads,
    load_uploaded_dataset,
    save_upload,
)

CSV = (
    "date,temp,load\n"
    "2024-01-01T00:00:00,1.5,10\n"
    "2024-01-01T01:00:00,2.5,20\n"
    "2024-01-01T02:00:00,,30\n"
)


@pytest.fixture(autouse=True)
def upload_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAMEND_UPLOAD_DIR", str(tmp_path / "uploads"))
    return tmp_path


def test_save_upload_profiles_columns_and_detects_timestamp():
    _, profile, _ = save_upload("series.csv", CSV.encode())

    assert profile.rowCount == 3
    assert profile.columnCount == 3
    assert profile.timestampColumn == "date"
    assert profile.signalColumns == ["temp", "load"]

    temp = next(column for column in profile.columns if column.name == "temp")
    assert temp.kind == "numeric"
    assert temp.nullCount == 1
    assert temp.min == 1.5
    assert temp.max == 2.5
    assert len(profile.preview) == 3


def test_load_uploaded_dataset_indexes_by_timestamp_and_drops_it():
    dataset_id, _, _ = save_upload("series.csv", CSV.encode())

    df = load_uploaded_dataset(dataset_id)

    assert isinstance(df.index, pd.DatetimeIndex)
    assert list(df.columns) == ["temp", "load"]
    assert df.index.is_monotonic_increasing


def test_load_uploaded_dataset_honours_explicit_timestamp_column():
    dataset_id, _, _ = save_upload("series.csv", CSV.encode())

    df = load_uploaded_dataset(dataset_id, timestamp_column="date")

    assert list(df.columns) == ["temp", "load"]


def test_load_uploaded_dataset_rejects_non_timestamp_column():
    dataset_id, _, _ = save_upload("series.csv", CSV.encode())

    with pytest.raises(UploadError, match="not valid timestamps"):
        load_uploaded_dataset(dataset_id, timestamp_column="temp")


def test_list_uploads_returns_saved_datasets():
    save_upload("a.csv", CSV.encode())
    save_upload("b.csv", CSV.encode())

    summaries = list_uploads()

    assert {summary.name for summary in summaries} == {"a.csv", "b.csv"}
    assert all(summary.rowCount == 3 for summary in summaries)


def test_unknown_dataset_id_is_rejected():
    with pytest.raises(UnknownDatasetError):
        load_uploaded_dataset("../../etc/passwd")


@pytest.mark.parametrize(
    "filename,content,message",
    [
        ("series.parquet", CSV.encode(), "Unsupported file type"),
        ("series.csv", b"", "empty"),
        ("series.csv", b"onlycolumn\n1\n2\n", "at least two columns"),
    ],
)
def test_save_upload_rejects_bad_input(filename, content, message):
    with pytest.raises(UploadError, match=message):
        save_upload(filename, content)


def test_detect_timestamp_column_prefers_named_column():
    df = pd.DataFrame(
        {
            "other": ["2024-01-01", "2024-01-02"],
            "timestamp": ["2024-02-01", "2024-02-02"],
            "value": [1.0, 2.0],
        }
    )

    assert detect_timestamp_column(df) == "timestamp"


def test_profile_dataframe_without_timestamp_column():
    profile = profile_dataframe(pd.DataFrame({"a": [1, 2], "b": [3, 4]}))

    assert profile.timestampColumn is None
    assert profile.signalColumns == ["a", "b"]
