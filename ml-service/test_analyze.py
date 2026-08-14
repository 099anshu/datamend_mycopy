import json
import urllib.request

BASE_URL = "http://localhost:8000"

ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]


def post_json(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def run_test() -> None:
    payload = {
        "analysisId": "ett-001",
        "datasetName": "ETTh1",
        "columns": ETTH1_COLUMNS,
        "detector": "timercd",
        "threshold": 0.8,
    }
    result = post_json("/api/v1/analyze", payload)

    assert result["status"] == "COMPLETED", result
    assert result["analysisId"] == payload["analysisId"], result
    assert result["detector"] == "timercd", result
    assert isinstance(result["anomalies"], list), result

    scores_payload = {key: value for key, value in payload.items() if key != "threshold"}
    scores_result = post_json("/api/v1/scores", scores_payload)
    assert scores_result["status"] == "COMPLETED", scores_result
    assert scores_result["analysisId"] == payload["analysisId"], scores_result
    assert scores_result["detector"] == "timercd", scores_result
    assert len(scores_result["scores"]) == 17420, scores_result
    print("PASS: ETTh1 loaded from TSDB and scored through both API endpoints")


if __name__ == "__main__":
    run_test()
