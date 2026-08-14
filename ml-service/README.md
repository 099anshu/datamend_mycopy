# ml-service

FastAPI anomaly-detection service backed by TSDB datasets and the TimeRCD
zero-shot detector.

## Endpoints

- `POST /api/v1/analyze` — run detection and return anomalies above a threshold.
- `POST /api/v1/scores` — run detection and return a per-timestamp score series.

## Missing value handling

TimeRCD does not support NaNs, so missing values must be handled explicitly.
An optional `missingValueHandling` object selects the strategy:

- `reject` (default) — if missing values are present, the request fails with
  HTTP 400 explaining that an imputation strategy must be selected.
- `ffill` — forward-fill (leading NaNs back-filled).
- `bfill` — backward-fill (trailing NaNs forward-filled).
- `mean` — fill with the per-column mean.
- `interpolate` — linear interpolation (edges filled).

No imputation is ever performed automatically, and no `0` fallback is applied.
When the data has no missing values, the data passes through unchanged. The
effective strategy is reported in the response as `missingValueHandling`.
Preprocessing always operates on a copy; original TSDB values are never
modified.

## Example: analyze with PyGrinder corruption and explicit imputation

Corruption is optional. When enabled, PyGrinder introduces missingness into a
copy of the data before scoring, the actual missing rate is reported, and the
original TSDB values are never modified. After corruption you must choose how
missing values are handled:

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

Response includes `missingRate` with the actual missing rate and
`missingValueHandling` with the effective strategy:

```json
{
  "analysisId": "ett-001",
  "status": "COMPLETED",
  "detector": "timercd",
  "anomalies": [],
  "missingRate": 0.1003,
  "missingValueHandling": "ffill"
}
```

Supported corruption methods: `mcar`, `mar_logistic`, `mnar_x`, `mnar_t`,
`mnar_nonuniform`, `rdo`, `seq_missing`, `block_missing`. Invalid methods,
parameters, or missing-value strategies return HTTP 400.
