# DataMend Testing Frontend

Minimal black-and-white developer/testing GUI for the DataMend anomaly-detection
pipeline. The page is served by the Spring Boot backend and talks **only** to
Spring Boot (never directly to the Python ml-service).

```
Frontend (browser, served by Spring Boot)
  -> Spring Boot backend (proxy: POST /api/v1/ml/analyze, /api/v1/ml/scores)
  -> Python FastAPI ml-service (POST /api/v1/analyze, /api/v1/scores)
  -> TSDB + TimeRCD
```

## How to run

1. Start the Python ml-service (port 8000):

   ```bash
   cd ml-service
   uv run uvicorn main:app --port 8000
   ```

2. Start the Spring Boot backend (port 8080). The proxy reads the ml-service
   URL from `application.yml` (`ml-service.base-url: http://localhost:8000`):

   ```bash
   cd backend
   ./mvnw spring-boot:run
   ```

3. Open the browser:

   ```
   http://localhost:8080/
   ```

   The static page (`index.html`, `styles.css`, `app.js`) is served directly
   by Spring Boot, so no separate frontend server or build step is needed.

## Test scenario

Use the GUI to run:

- Dataset: `ETTh1`
- Columns: `HUFL,HULL,MUFL,MULL,LUFL,LULL,OT`
- Detector: `timercd`
- Threshold: `0.8`
- Corruption: enable, method `mcar`, `p: 0.10`
- Missing-value handling: `ffill`

Then click **Analyze** to see the returned anomalies, `missingRate`, and
`missingValueHandling`, and **Get Scores** for the raw per-timestamp scores.

## Backend proxy endpoints

| Endpoint | Forwards to ml-service |
| --- | --- |
| `POST /api/v1/ml/analyze` | `POST /api/v1/analyze` |
| `POST /api/v1/ml/scores` | `POST /api/v1/scores` |

## Notes

- The backend only routes, validates, and relays; all ML logic (TSDB loading,
  PyGrinder corruption, missing-value handling, TimeRCD inference) lives in
  the ml-service.
- First TimeRCD inference downloads the pretrained checkpoint from Hugging
  Face Hub (cached afterward). Full-ETTh1 scoring may take ~30s.
