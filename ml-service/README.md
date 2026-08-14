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

## TimeRCD Zero-Shot Inference

TimeRCD is used as a **pretrained, zero-shot anomaly detector**. It is never
trained or fine-tuned on the target dataset. The anomaly score is the
**anomalous-class probability** produced by TimeRCD's anomaly head (the
reconstruction head is not used for scoring), computed per timestep in
`[0, 1]`. Thresholding is applied separately in the API layer:
`anomaly = score >= threshold`.

Configuration (set before starting the server):

| Variable | Default | Description |
| --- | --- | --- |
| `TIMERCD_CHECKPOINT_PATH` | unset | Path to a local `.pth` checkpoint. When set, the detector loads it via `from_local`; a missing file raises `FileNotFoundError`. When unset, the packaged Hugging Face `from_pretrained` default (`thu-sail-lab/Time-RCD`) is used. |
| `TIMERCD_WIN_SIZE` | `5000` | Context window length in timesteps (matches the TimeRCD paper's main evaluation setup). Sequences shorter than the window use their full length. |

Example:

```bash
# Use a local checkpoint with a 5000-timestep window
TIMERCD_CHECKPOINT_PATH=/path/to/pretrain_checkpoint_best_multi.pth \
TIMERCD_WIN_SIZE=5000 \
uv run uvicorn main:app
```

Because the detector reads these variables when it is first constructed, set
them before starting the server (or restart the server to apply changes).

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

Run TimeRCD zero-shot verification tests:

```bash
uv run pytest detectors -q
```
