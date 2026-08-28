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
* `POST /api/v1/datasets/live` — fetch a fresh dataset from a live public API
  (`source: "weather"` via Open-Meteo, `source: "crypto"` via CoinGecko) and
  ingest it as a normal dataset, ready for profiling/validation/analysis.
* `POST /api/v1/validate/suggest` — auto-detect a dataset's columns and
  propose default rule-based validation rules (range/not-null/data-type).
* `POST /api/v1/validate` — run rule-based validation (Objective #2: range
  check, not-null, data type, uniqueness, cross-field) against a dataset and
  return a `ValidationReport` with a 0–100 quality score.

See `validation/rule_based.py` and `datasets/live_api_loader.py` for details.

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
uv run python -m evaluation.experiment_runner \
  --dataset ETTh1 \
  --anomaly-rate 0.01 \
  --seed 0
```

With 10% MCAR missingness:

```bash
uv run python -m evaluation.experiment_runner \
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

**Note**: The old `evaluation.evaluate_timercd` module is deprecated. Use `evaluation.experiment_runner` instead.

## Testing

Run all tests:

```bash
uv run pytest -q
```

Run unit tests:

```bash
uv run pytest tests/unit/ -q
```

Run integration tests:

```bash
uv run pytest tests/integration/ -q
```

Run evaluation tests:

```bash
uv run pytest tests/unit/metrics/ -q
```

Run API and corruption tests:

```bash
uv run pytest tests/integration/api/ tests/unit/corruption/ -q
```

Run TimeRCD zero-shot verification tests:

```bash
uv run pytest tests/unit/detectors/ -q
```

## Synthetic Dataset Generation

The `datasets/synthetic` module provides synthetic and semi-synthetic dataset generation for controlled evaluation with ground-truth labels.

### Quick Start

```bash
# Generate univariate synthetic dataset
uv run python scripts/generate_synthetic.py generate \
  --num-samples 100 \
  --seq-len 1000 \
  --anomaly-ratio 1.0 \
  --output synthetic_univariate.pkl

# Generate multivariate synthetic dataset (5 features)
uv run python scripts/generate_synthetic.py generate \
  --num-samples 50 \
  --seq-len 1000 \
  --anomaly-ratio 1.0 \
  --multivariate \
  --num-features 5 \
  --output synthetic_multivariate.pkl

# Generate with specific anomaly types
uv run python scripts/generate_synthetic.py generate \
  --num-samples 100 \
  --metrics spike,drift,trend_break \
  --output synthetic_spike_drift.pkl
```

### Semi-Synthetic Evaluation (TSDB + Injected Anomalies)

```bash
# Inject anomalies into ETTh1 with clean window detection
uv run python scripts/generate_synthetic.py inject-tsdb ETTh1 \
  --intensity 3.0 \
  --count 5 \
  --placement random \
  --output semi_synthetic_etth1.pkl

# Target specific sensors
uv run python scripts/generate_synthetic.py inject-tsdb ETTh1 \
  --sensors HUFL,MUFL \
  --metrics spike,drift \
  --output semi_synthetic_targeted.pkl
```

### Benchmarking

```bash
# Run benchmark on synthetic data
uv run python scripts/generate_synthetic.py benchmark \
  --type synthetic \
  --multivariate \
  --num-features 5 \
  --strategy best_f1

# Run benchmark on semi-synthetic data
uv run python scripts/generate_synthetic.py benchmark \
  --type semi_synthetic \
  --tsdb-dataset ETTh1 \
  --strategy best_f1

# Run with fixed threshold
uv run python scripts/generate_synthetic.py benchmark \
  --type synthetic \
  --threshold 0.8

# Save baseline for regression testing
uv run python scripts/generate_synthetic.py benchmark \
  --type synthetic \
  --save-baseline timercd_synthetic_baseline
```

### CI/CD Regression Testing

```bash
# Run CI benchmarks (compares against baselines)
uv run python scripts/generate_synthetic.py ci-benchmark

# Update baselines after verified improvements
uv run python scripts/generate_synthetic.py ci-benchmark --update-baselines

# Generate markdown report
uv run python scripts/generate_synthetic.py ci-benchmark --output-report ci_report.md
```

### Evaluation with Synthetic Data

```bash
# Run evaluation on synthetic data
uv run python -m evaluation.evaluate_timercd \
  --dataset-type synthetic \
  --num-samples 100 \
  --seq-len 1000 \
  --anomaly-rate 1.0 \
  --seed 42

# Run evaluation on multivariate synthetic data
uv run python -m evaluation.evaluate_timercd \
  --dataset-type synthetic \
  --multivariate \
  --num-features 5 \
  --num-samples 50 \
  --seq-len 1000 \
  --anomaly-rate 1.0

# Run evaluation on semi-synthetic data
uv run python -m evaluation.evaluate_timercd \
  --dataset-type semi_synthetic \
  --dataset ETTh1 \
  --injection-intensity 3.0 \
  --injection-count 5
```

### Supported Anomaly Types

```bash
uv run python scripts/generate_synthetic.py list-anomalies
```

Output:
- `spike` - Point anomaly (instantaneous)
- `drop` - Point drop anomaly
- `drift` - Gradual drift
- `trend_break` - Trend slope change
- `seasonality_break` - Seasonality disruption
- `noise_increase` - Increased variance
- `level_shift` - Permanent step change
- `pattern_change` - Frequency/phase shift

### Supported Pattern Types

```bash
uv run python scripts/generate_synthetic.py list-patterns
```

Output:
- `stationary` - No trend, no seasonality
- `linear_trend` - Linear trend
- `quadratic_trend` - Quadratic trend
- `single_seasonal` - Single seasonality
- `multi_seasonal` - Multiple seasonalities
- `trend_and_seasonal` - Trend + seasonality
- `high_noise` - High noise AR process
- `low_noise` - Low noise AR process
