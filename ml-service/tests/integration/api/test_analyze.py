import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]


def _base(corruption=None, missing_value_handling=None):
    payload = {
        "analysisId": "ett-001",
        "datasetName": "ETTh1",
        "columns": ETTH1_COLUMNS,
        "detector": "timercd",
        "threshold": 0.8,
    }
    if corruption is not None:
        payload["corruption"] = corruption
    if missing_value_handling is not None:
        payload["missingValueHandling"] = missing_value_handling
    return payload


def test_analyze_endpoint():
    """Test /api/v1/analyze endpoint with clean data."""
    payload = _base()
    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["analysisId"] == payload["analysisId"]
    assert body["detector"] == "timercd"
    assert isinstance(body["anomalies"], list)


def test_scores_endpoint():
    """Test /api/v1/scores endpoint with clean data."""
    payload = {k: v for k, v in _base().items() if k != "threshold"}
    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["analysisId"] == payload["analysisId"]
    assert body["detector"] == "timercd"
    assert len(body["scores"]) == 17420  # ETTh1 length


def test_analyze_with_corruption_and_ffill():
    """Test analyze with MCAR corruption and ffill strategy."""
    payload = _base(
        corruption={"enabled": True, "method": "mcar", "params": {"p": 0.1}},
        missing_value_handling={"strategy": "ffill"},
    )
    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["missingValueHandling"] == "ffill"
    assert body["missingRate"] > 0.0


def test_scores_with_corruption_and_ffill():
    """Test scores with MCAR corruption and ffill strategy."""
    payload = {
        "analysisId": "ett-001",
        "datasetName": "ETTh1",
        "columns": ETTH1_COLUMNS,
        "detector": "timercd",
        "corruption": {"enabled": True, "method": "mcar", "params": {"p": 0.1}},
        "missingValueHandling": {"strategy": "ffill"},
    }
    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["missingValueHandling"] == "ffill"
    assert body["missingRate"] > 0.0
    assert len(body["scores"]) == 17420