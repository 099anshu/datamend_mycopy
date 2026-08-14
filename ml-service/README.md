````markdown
# ml-service

FastAPI anomaly-detection service using TSDB datasets and the TimeRCD detector.

## Setup

```bash
uv sync
````

Start the API:

```bash
uv run uvicorn main:app --reload
```

API:

```text
http://localhost:8000
```

## Endpoints

* `POST /api/v1/analyze` — detect anomalies above a threshold.
* `POST /api/v1/scores` — return anomaly scores for every timestamp.

## Datasets

Datasets are loaded using [TSDB](https://github.com/WenjieDu/TSDB).

Example dataset:

```text
ETTh1
```

TSDB downloads and caches datasets automatically.

## Missing Value Handling

TimeRCD does not support NaN values, so missing values must be handled explicitly.

Supported strategies:

* `reject` — default; returns HTTP 400 if NaNs are present.
* `ffill` — forward-fill, then back-fill leading NaNs.
* `bfill` — backward-fill, then forward-fill trailing NaNs.
* `mean` — per-column mean.
* `interpolate` — linear interpolation with edge filling.

No missing-value handling is performed automatically.

Example:

```json
{
  "missingValueHandling": {
    "strategy": "ffill"
  }
}
```

## PyGrinder Corruption

[PyGrinder](https://github.com/WenjieDu/PyGrinder) can optionally introduce synthetic missing values.

Supported methods:

```text
mcar
mar_logistic
mnar_x
mnar_t
mnar_nonuniform
rdo
seq_missing
block_missing
```

Example:

```json
{
  "corruption": {
    "enabled": true,
    "method": "mcar",
    "params": {
      "p": 0.1
    }
  },
  "missingValueHandling": {
    "strategy": "ffill"
  }
}
```

The response reports the actual missing rate:

```json
{
  "missingRate": 0.1003,
  "missingValueHandling": "ffill"
}
```

Original TSDB data is never modified.

## Example Request

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "analysisId": "ett-001",
    "datasetName": "ETTh1",
    "columns": ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"],
    "detector": "timercd",
    "threshold": 0.8,
    "corruption": {
      "enabled": true,
      "method": "mcar",
      "params": {"p": 0.1}
    },
    "missingValueHandling": {
      "strategy": "ffill"
    }
  }'
```

## Evaluation

A basic TimeRCD evaluation can be run with:

```bash
uv run python -m evaluation.evaluate_timercd \
  --dataset ETTh1 \
  --anomaly-rate 0.01 \
  --seed 0
```

With 10% MCAR missingness:

```bash
uv run python -m evaluation.evaluate_timercd \
  --dataset ETTh1 \
  --anomaly-rate 0.01 \
  --seed 0 \
  --missingness mcar \
  --p 0.10 \
  --strategy ffill
```

The evaluation reports:

```text
Precision
Recall
F1
PR-AUC
ROC-AUC
```

## Testing

Run all tests:

```bash
uv run pytest -q
```

Run evaluation tests:

```bash
uv run pytest evaluation -q
```

Run API and corruption tests:

```bash
uv run pytest test_corruption.py test_api.py -q
```
