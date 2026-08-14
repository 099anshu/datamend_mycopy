import json
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

BASE_URL = "http://localhost:8000"


def build_spike_csv(path: Path) -> str:
    t = np.arange(0, 1000, 1)
    signal = np.sin(t / 20.0)
    signal[700] = 50.0
    df = pd.DataFrame({"timestamp": t, "value": signal})
    df.to_csv(path, index=False)
    return str(path)


def run_test() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "spike.csv"
        dataset_path = build_spike_csv(path)

        payload = {
            "analysisId": "test-1",
            "datasetPath": dataset_path,
            "timestampColumn": "timestamp",
            "columns": ["value"],
            "detector": "timercd",
        }
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/analyze",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())

    assert result["status"] == "COMPLETED", result
    assert result["analysisId"] == "test-1", result
    assert len(result["anomalies"]) > 0, "expected at least one anomaly"

    spike_row = result["anomalies"][700]
    print(f"spike anomaly: ts={spike_row['timestamp']} value={spike_row['value']} "
          f"score={spike_row['score']} severity={spike_row['severity']}")
    assert float(spike_row["value"]) == 50.0
    assert float(spike_row["score"]) > 0.9, f"spike score too low: {spike_row['score']}"
    assert spike_row["severity"] == "HIGH"

    high_scores = [a for a in result["anomalies"] if float(a["score"]) > 0.9]
    print(f"HIGH anomalies: {len(high_scores)}")
    print("PASS: spike detected with high score")


if __name__ == "__main__":
    run_test()