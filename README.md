# DataMend

**DataMend** is a modular time-series anomaly detection platform. It combines automated dataset acquisition via **TSDB**, synthetic corruption injection via **PyGrinder**, zero-shot foundation model anomaly detection via **TimeRCD**, and a **Next.js 14** visualization dashboard with real-time **Server-Sent Events (SSE)**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Next.js 14 Web Frontend (:3000)                     │
│  Interactive Multi-Series, Anomaly Heatmaps, Observable Deltas, SSE    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  POST /api/v1/ml/analyze
                                    │  POST /api/v1/ml/scores
                                    │  GET  /api/v1/analyses/{id}/events (SSE)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Spring Boot Backend Core (:8080)                    │
│   ML Orchestration · Modular Dataset Service · CORS · SSE Emitter      │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │ JDBC
                   │ POST /api/v1/analyze            ▼
                   │ POST /api/v1/scores       ┌────────────┐
                   ▼                           │ PostgreSQL │
┌──────────────────────────────────────┐       │   :5433    │
│          Python ml-service           │       └─────▲──────┘
│            FastAPI :8000             │             │
│   (TimeRCD + TSDB + PyGrinder MVH)   │ ────────────┘
└──────────────────────────────────────┘   anomalies persisted
```

---

## Architecture & Responsibilities

| Layer | Directory | Technology | Role & Key Capabilities |
|---|---|---|---|
| **Frontend** | `frontend/` | Next.js 14, TypeScript, Recharts | Interactive time-series exploration, anomaly overlays, score distribution, and live SSE progress tracking. |
| **Backend Core** | `backend/` | Spring Boot 3 (Java 17, Maven) | Modular dataset provider layer, asynchronous job orchestration, SSE broadcasting, and Flyway migrations. |
| **ML Service** | `ml-service/` | Python 3.10 (uv, FastAPI, PyTorch) | Zero-shot TimeRCD detector inference, TSDB automatic dataset fetching, PyGrinder missingness injection, and MVH imputation. |
| **Database** | — | PostgreSQL 16 (Docker) | Relational persistence of datasets, analysis job states, and detected anomaly logs. |
| **Legacy GUI** | `backend/src/main/resources/static/` | Vanilla JS / HTML | Static developer testing UI with asynchronous SSE/polling support. |

---

## Quick Start Guide

### Prerequisites
- **Docker & Docker Compose** (for PostgreSQL)
- **Node.js 18+** & `npm`
- **Java 17+**
- **Python 3.10+** with `uv` (`curl -LsSf https://astral.sh/uv/install.ps1 | iex` on Windows)

---

### Step-by-Step Execution

#### 1. Start the Database (PostgreSQL 16)
```sh
docker compose up -d
```
*Runs PostgreSQL on `localhost:5433` (DB: `timeseries`, User: `dev`, Password: `dev`).*

#### 2. Start the Python ML Service
```sh
cd ml-service
uv run uvicorn main:app --port 8000
```
*Starts FastAPI on `http://localhost:8000` with TimeRCD zero-shot inference.*

#### 3. Start the Spring Boot Backend Core
```sh
cd backend
./mvnw spring-boot:run
```
*Starts Spring Boot on `http://localhost:8080` with auto-applied Flyway migrations, CORS enabled for `:3000`, and active SSE emitters.*

#### 4. Start the Next.js Frontend
```sh
cd frontend
npm install
npm run dev
```
*Launches the dashboard at [http://localhost:3000](http://localhost:3000).*

---

## Data Flow & Processing Pipeline

1. **Explore Time-Series & Initial Scoring**:
   - The frontend calls `POST /api/v1/ml/scores` with the chosen dataset and columns.
   - The ML service loads the time-series via **TSDB**, applies optional corruption & missing-value handling, and executes continuous TimeRCD scoring.
   - Raw timestamps, feature values, and per-step anomaly scores are rendered immediately on the dashboard.

2. **Trigger Asynchronous Anomaly Detection**:
   - The user clicks **"Run Anomaly Detection"**, sending `POST /api/v1/ml/analyze`.
   - Spring Boot's `DatasetService` resolves/creates the dataset record, generates a unique `analysisId`, and starts an asynchronous execution thread.
   - Spring Boot returns `{ "analysisId": "...", "status": "RUNNING" }` immediately.

3. **Real-Time Streaming via Server-Sent Events (SSE)**:
   - The frontend connects to `GET /api/v1/analyses/{id}/events` via an `EventSource`.
   - When TimeRCD inference completes, Spring Boot persists all detected anomalies into PostgreSQL and broadcasts the completed payload over SSE.
   - Fallback polling (`GET /api/v1/analyses/{id}`) is activated automatically if the browser disconnects.

---

## Key API Endpoints

| Endpoint | Method | Description | Request / Response Summary |
|---|---|---|---|
| `/api/v1/ml/scores` | `POST` | Synchronous endpoint returning all series points & scores | **Body**: `{ datasetName, columns, detector, threshold, corruption, missingValueHandling }`<br/>**Returns**: `{ scores: [{ timestamp, values, score, severity }], missingRate }` |
| `/api/v1/ml/analyze` | `POST` | Asynchronous trigger starting anomaly analysis job | **Body**: Same payload structure as `/scores`<br/>**Returns**: `{ analysisId: "UUID", status: "RUNNING" }` |
| `/api/v1/analyses/{id}` | `GET` | REST endpoint retrieving status and persisted anomalies | **Returns**: `{ id, status: "COMPLETED", detector, anomalies: [...] }` |
| `/api/v1/analyses/{id}/events` | `GET` | Server-Sent Events stream for real-time lifecycle updates | **Events**: `connected`, `status`, `completed`, `failed` |

---

## Time-Series Visualization Capabilities

Inspired by ObservableHQ & Python Time-Series visualization standards:

- **Multivariate Sensor Stream with Anomaly Overlay**: Interactive multi-line chart supporting zooming, panning (Brush), and severity markers (Rose = HIGH, Amber = MEDIUM, Sky = LOW).
- **Observable Baseline Deviation Chart**: Visualizes true vertical differences $\Delta(t) = y(t) - \bar{y}_{SMA}(t)$ on a zero-aligned baseline rather than optical curvature.
- **Dynamic Rolling Simple Moving Average (SMA)**: User-selectable smoothing window (6h, 12h, 24h, 48h, 7d).
- **TimeRCD Anomaly Score Curve**: Real-time visualization of model confidence score alongside the active decision threshold boundary.
- **Feature × Time Anomaly Heatmap**: Dense spatio-temporal matrix exposing multi-channel anomaly clusters.
- **Severity & Channel Distributions**: Donut and bar charts showing anomaly classification proportions.
- **Incident Inspection Table**: Searchable, filterable log with JSON export for report generation.

---

## Test Scenario

1. In the Next.js UI ([http://localhost:3000](http://localhost:3000)), configure:
   - **Dataset**: `ETTh1` (Electricity Transformer Hourly 1)
   - **Columns**: `HUFL,HULL,MUFL,MULL,LUFL,LULL,OT`
   - **Detector**: `timercd`
   - **Threshold**: `0.80`
   - **PyGrinder Corruption**: Enable $\rightarrow$ Method: `mcar` $\rightarrow$ $p = 0.10$
   - **Imputation Strategy**: `ffill`
2. Click **"1. Load Series & Scores"** to inspect data points and baseline score distribution.
3. Click **"2. Run Anomaly Detection"** to trigger async processing and watch live SSE events populate the anomaly logs.

---

## Project Structure

```
DataMend/
├── backend/                              # Spring Boot 3 Core Service
│   ├── src/main/java/com/datamend/backend/
│   │   ├── config/                       # CORS & WebMvc configurations
│   │   ├── controller/                   # Proxy & Analysis REST/SSE controllers
│   │   ├── dto/                          # Request/Response data transfer objects
│   │   ├── entity/                       # JPA entities (Analysis, Anomaly, Dataset)
│   │   ├── repository/                   # Spring Data JPA repositories
│   │   └── service/
│   │       ├── dataset/                  # Modular DatasetProvider & TSDB resolver
│   │       ├── event/                    # SSE EventService emitter manager
│   │       └── orchestration/            # Async analysis orchestrator
│   └── src/main/resources/
│       ├── application.yml               # Backend configuration
│       ├── db/migration/                 # Flyway SQL migrations
│       └── static/                       # Legacy developer testing GUI (app.js, index.html)
├── frontend/                             # Next.js 14 Dashboard Application
│   ├── src/
│   │   ├── app/                          # App Router (page.tsx, layout.tsx, globals.css)
│   │   ├── components/                   # Recharts visualizations & interactive controls
│   │   ├── lib/                          # API client, SSE subscriber, transform utils
│   │   └── types/                        # Strict TypeScript data models
│   ├── package.json                      # Next.js, React 18, Recharts dependencies
│   └── tsconfig.json                     # TypeScript strict configuration
├── ml-service/                           # Python 3.10 FastAPI ML Service
│   ├── main.py                           # FastAPI application endpoints
│   ├── detectors/                        # TimeRCD zero-shot inference engine
│   ├── corruption/                       # PyGrinder missingness injection
│   └── pyproject.toml                    # uv package manager definition
├── docker-compose.yml                    # PostgreSQL 16 service
└── README.md
```
