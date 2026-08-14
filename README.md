# DataMend

Modular monolith for time-series anomaly detection: CSV data flows in, is processed and stored, machine learning identifies anomalies, and a dashboard visualizes the results.

```
┌────────────┐   upload    ┌──────────────┐   JDBC    ┌────────────┐
│  CSV       │ ──────────▶ │ Spring Boot  │ ────────▶ │ PostgreSQL │
│  upload    │             │ backend      │           │ timeseries │
└────────────┘             └──────┬───────┘           └─────▲──────┘
                                  │                         │
                                 data                       data
                                  ▼                         │
                            ┌────────────┐                  │
                            │ Python ML  │ ────────────────┘
                            │ ml-service │  anomaly results
                            │  (TimeRCD) │
                            └──────┬─────┘
                                   │
                                   ▼
                             ┌────────────┐
                             │  Next.js   │
                             │  dashboard │
                             └────────────┘
```

## Architecture

A **modular monolith**, not microservices: one repository, one shared database, three cooperating services that are independently developable and deployable.

| Layer | Directory | Stack | Responsibility |
|-------|-----------|-------|----------------|
| API core | `backend/` | Spring Boot (Java 21, Maven) | CSV intake, orchestration, persistence |
| Processing | `ml-service/` | Python (uv-managed) | Time-series analysis with TimeRCD, anomaly detection |
| UI | `frontend/` | Next.js (TypeScript, App Router) | Dashboard, anomaly visualization, upload UX |
| Storage | — | PostgreSQL 16 | Time-series + anomaly results storage |

### Data flow

1. CSV file uploaded to Spring Boot (`backend/`)
2. Spring Boot persists raw data to PostgreSQL
3. Python ML service (`ml-service/`) reads series, applies TimeRCD
4. Anomaly results written back to PostgreSQL
5. Next.js dashboard (`frontend/`) reads results from Spring Boot and renders them

## Setup

> Placeholders — service setup instructions will be added in later steps as each layer is scaffolded.

### 1. Environment

Copy `.env.example` to `.env` and adjust as needed:

```sh
cp .env.example .env
```

### 2. Database

```sh
docker compose up -d
```

Postgres starts on `localhost:5432` with database `timeseries`, user `dev`, password `dev`. Data persists in the `pgdata` named volume.

### 3. Services — *placeholder*

### 4. Verify — *placeholder*

## Project layout

```
DataMend/
├── backend/          Spring Boot service (empty — to be scaffolded)
├── ml-service/       Python ML service (uv — empty — to be scaffolded)
├── frontend/         Next.js dashboard (empty — to be scaffolded)
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```