import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]


def _base(corruption=None, missing_value_handling=None):
    payload = {
        "analysisId": "mvh-api",
        "datasetName": "ETTh1",
        "columns": ETTH1_COLUMNS,
        "detector": "timercd",
    }
    if corruption is not None:
        payload["corruption"] = corruption
    if missing_value_handling is not None:
        payload["missingValueHandling"] = missing_value_handling
    return payload


def test_clean_data_no_strategy_succeeds_with_reject_reported():
    response = client.post("/api/v1/analyze", json=_base())
    assert response.status_code == 200
    body = response.json()
    assert body["missingValueHandling"] == "reject"
    assert "missingRate" not in body


def test_corruption_with_default_reject_returns_400():
    payload = _base(
        corruption={"enabled": True, "method": "mcar", "params": {"p": 0.1}}
    )
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 400
    assert "TimeRCD" in response.json()["detail"]
    assert "missingValueHandling" in response.json()["detail"]


def test_corruption_with_explicit_ffill_succeeds():
    payload = _base(
        corruption={"enabled": True, "method": "mcar", "params": {"p": 0.1}},
        missing_value_handling={"strategy": "ffill"},
    )
    response = client.post("/api/v1/scores", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["missingValueHandling"] == "ffill"
    assert body["missingRate"] > 0.0
    assert len(body["scores"]) > 0


def test_unsupported_strategy_returns_400():
    payload = _base(missing_value_handling={"strategy": "not_a_strategy"})
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 400
    assert "Supported strategies" in response.json()["detail"]


def test_reject_strategy_is_reported_on_scores_endpoint():
    response = client.post("/api/v1/scores", json=_base())
    assert response.status_code == 200
    assert response.json()["missingValueHandling"] == "reject"