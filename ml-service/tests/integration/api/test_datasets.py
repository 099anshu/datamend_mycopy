import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

CSV = b"date,temp,load\n2024-01-01T00:00:00,1.5,10\n2024-01-01T01:00:00,2.5,20\n"


@pytest.fixture(autouse=True)
def upload_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAMEND_UPLOAD_DIR", str(tmp_path / "uploads"))


def _upload(filename: str = "series.csv", content: bytes = CSV):
    return client.post(
        "/api/v1/datasets",
        files={"file": (filename, content, "text/csv")},
    )


def test_upload_returns_profile():
    response = _upload()

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "series.csv"
    assert body["source"] == "upload"
    assert body["profile"]["timestampColumn"] == "date"
    assert body["profile"]["signalColumns"] == ["temp", "load"]


def test_uploaded_dataset_is_retrievable_and_listed():
    dataset_id = _upload().json()["datasetId"]

    detail = client.get(f"/api/v1/datasets/{dataset_id}")
    assert detail.status_code == 200
    assert detail.json()["datasetId"] == dataset_id

    listing = client.get("/api/v1/datasets")
    assert listing.status_code == 200
    assert [item["datasetId"] for item in listing.json()] == [dataset_id]


def test_upload_rejects_unsupported_file_type():
    response = _upload(filename="series.xlsx")

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_get_unknown_dataset_returns_404():
    assert client.get("/api/v1/datasets/deadbeef").status_code == 404


def test_scores_on_unknown_uploaded_dataset_returns_404():
    response = client.post(
        "/api/v1/scores",
        json={
            "analysisId": "upload-missing",
            "datasetName": "0" * 32,
            "columns": ["temp"],
            "detector": "timercd",
            "source": "upload",
        },
    )

    assert response.status_code == 404


def test_analysis_rejects_unknown_source():
    response = client.post(
        "/api/v1/scores",
        json={
            "analysisId": "bad-source",
            "datasetName": "whatever",
            "columns": ["temp"],
            "detector": "timercd",
            "source": "ftp",
        },
    )

    assert response.status_code == 422


def test_tsdb_sources_are_listed():
    response = client.get("/api/v1/datasets/sources/tsdb")

    assert response.status_code == 200
    assert "ETTh1" in response.json()
