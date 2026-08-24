# DataMend

Modular monolith for time-series anomaly detection: CSV data flows in, machine learning identifies anomalies, and a web GUI visualizes the results.

```
┌─────────────────────────────────────┐
│        Browser                      │
│   static GUI (served by Spring Boot)│
└──────────────┬──────────────────────┘
               │  /api/v1/ml/analyze, /api/v1/ml/scores
               ▼
┌──────────────────────┐   JDBC    ┌────────────┐
│    Spring Boot       │ ────────▶ │ PostgreSQL │
│    backend :8080     │           │   :5433    │
└──────────┬───────────┘           └─────▲──────┘
           │  POST /api/v1/analyze       │
           │  POST /api/v1/scores        │
           ▼                             │
┌──────────────────────┐                │
│   Python ml-service   │ ───────────────┘
│   FastAPI :8000       │  anomaly results
│   (TimeRCD + TSDB)    │
└──────────────────────┘
```

## Architecture

A **modular monolith**, not microservices: one repository, one shared database, three cooperating services that are independently developable and deployable.

| Layer | Directory | Stack | Responsibility |
|-------|-----------|-------|----------------|
| API core | `backend/` | Spring Boot (Java 17, Maven) | ML orchestration proxy, serves the static GUI, Flyway migrations |
| Processing | `ml-service/` | Python 3.10 (uv-managed, FastAPI) | Time-series analysis with TimeRCD, anomaly detection, missing-value handling |
| UI | `backend/src/main/resources/static/` | Static HTML/CSS/JS (no build step) | Developer/testing GUI served directly by Spring Boot |
| Storage | — | PostgreSQL 16 | Time-series + anomaly results storage |

> The `frontend/` directory currently holds documentation only; the actual GUI lives in `backend/src/main/resources/static/`.

### Data flow

1. The static GUI (in the browser) calls the Spring Boot backend proxy
2. Spring Boot relays to the Python ml-service (`POST /api/v1/analyze`, `POST /api/v1/scores`)
3. The ml-service loads the series via TSDB, optionally corrupts it (PyGrinder), applies missing-value handling, and runs TimeRCD inference
4. Anomaly results are returned to the GUI through the backend proxy
5. The GUI renders the returned anomalies, `missingRate`, and raw per-timestamp scores

## Setup

### Option A: Docker PostgreSQL (recommended, port 5433)

```sh
docker compose up -d
```

Postgres starts on `localhost:5433` with database `timeseries`, user `dev`, password `dev`. Data persists in the `pgdata` named volume.

### Option B: Local PostgreSQL (port 5432)

Install PostgreSQL locally, then run with the `local` profile:

```sh
cd backend
SPRING_PROFILES_ACTIVE=local ./mvnw spring-boot:run
```

Defaults for local profile: `localhost:5432`, database `timeseries`, user `postgres`, password `postgres`.

**Override via environment variables** (works with both options):

```sh
export DB_URL=jdbc:postgresql://localhost:5432/timeseries
export DB_USER=postgres
export DB_PASSWORD=your_password
cd backend
./mvnw spring-boot:run
```

Required variables: `DB_URL`, `DB_USER`, `DB_PASSWORD`.

### 2. Python ml-service (port 8000)

```sh
cd ml-service
uv run uvicorn main:app --port 8000
```

### 3. Spring Boot backend (port 8080)

```sh
cd backend
./mvnw spring-boot:run
```

The proxy reads the ml-service URL from `application.yml` (`ml-service.base-url: http://localhost:8000`). Java 17+ is required.

### 4. Open the GUI

```
http://localhost:8080/
```

The static page (`index.html`, `styles.css`, `app.js`) is served directly by Spring Boot — no separate frontend server or build step is needed.

## Test scenario

Use the GUI to run:

- Dataset: `ETTh1`
- Columns: `HUFL,HULL,MUFL,MULL,LUFL,LULL,OT`
- Detector: `timercd`
- Threshold: `0.8`
- Corruption: enable, method `mcar`, `p: 0.10`
- Missing-value handling: `ffill`

Then click **Analyze** to see the returned anomalies, `missingRate`, and `missingValueHandling`, and **Get Scores** for the raw per-timestamp scores.

> First TimeRCD inference downloads the pretrained checkpoint from Hugging Face Hub (cached afterward). Full-ETTh1 scoring may take ~30s.

## Backend proxy endpoints

| Endpoint | Forwards to ml-service |
| --- | --- |
| `POST /api/v1/ml/analyze` | `POST /api/v1/analyze` |
| `POST /api/v1/ml/scores` | `POST /api/v1/scores` |

## Project layout

```
DataMend/
├── backend/                 Spring Boot service (Java 17, Maven)
│   └── src/main/resources/  application.yml, Flyway migrations, static GUI (index.html, styles.css, app.js)
├── ml-service/              Python ML service (uv, FastAPI)
│   ├── main.py              FastAPI app (analyze, scores)
│   ├── detectors/           TimeRCD and other detectors
│   ├── corruption/          PyGrinder corruption methods
│   └── pyproject.toml       Dependencies and Python 3.10 pin
├── frontend/                Frontend docs (the GUI itself lives in backend/ static resources)
├── docker-compose.yml       PostgreSQL 16 (port 5433)
├── .env.example
├── README.md
└── .gitignore
```
