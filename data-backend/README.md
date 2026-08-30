# CivSight — Data Pipeline + Data Backend (Nikita's layer)

Implements the "existing/planned data → actual ground data → unified
infrastructure intelligence" layer for CivSight (SIH26122):

- ETL pipeline: Extract → Validate → Clean → Transform → Geospatial → Load
- Unified PostgreSQL/PostGIS database (planned vs actual, citizen evidence, GIS)
- Read-only Data/Analytics API (FastAPI) — the endpoints Chetan's frontend and
  Avinash's AI/risk engine consume

**Ownership split (kept strict on purpose to avoid merge conflicts):**
- Nikita → this repo: `/projects`, `/projects/{id}/*`, `/infrastructure`, `/map/*`, `/analytics/*` (all read-only, data/analytics)
- Chetan → separate service: business/application APIs that WRITE (assign officer, update status, verify completion)

## 1. Install

```bash
cd civsight-data-backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You also need PostgreSQL with the PostGIS extension available. Easiest path — Docker:

```bash
docker run -d --name civsight-db \
  -e POSTGRES_USER=civsight_user \
  -e POSTGRES_PASSWORD=civsight_pass \
  -e POSTGRES_DB=civsight \
  -p 5432:5432 \
  postgis/postgis:16-3.4
```

## 2. Configure

```bash
cp .env.example .env
# edit .env if your DB isn't on localhost:5432 with the default credentials
```

## 3. Create the schema

```bash
python scripts/init_db.py
```

This runs `db/schema.sql` — creates all tables, the PostGIS extension, enums, and indexes.

## 4. Load data

If you don't have real government data yet, generate realistic sample data first:

```bash
python scripts/generate_sample_data.py
```

This writes `data/raw/projects.csv`, `facilities.csv`, `district_population.csv`,
`network.csv`. Replace any of these with real extracts later — the ETL code
doesn't change, only what's in `data/raw/`.

Then run the pipeline:

```bash
python scripts/run_etl.py
```

Watch the log — it prints how many rows were extracted, how many were rejected
by validation (and why, in `data/processed/rejected_projects.csv`), and how
many were finally loaded.

## 5. Run the API

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` — interactive Swagger UI for every endpoint
below. That's the fastest way to hand this off to teammates.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /projects` | List/filter projects (status, district, category, min deviation) |
| `GET /projects/{id}` | Single project detail incl. planned vs actual + deviation |
| `GET /projects/{id}/nearby` | Nearby population, critical facilities, connectivity impact notes |
| `GET /projects/{id}/analytics` | Schedule health, days remaining, citizen report counts |
| `GET /projects/{id}/history` | Full historical_updates timeline |
| `GET /infrastructure` | Raw road/rail network + facilities feed |
| `GET /map/infrastructure` | Lightweight, color-coded pins for the dashboard map |
| `GET /analytics/district` | District-level rollups for summary cards/charts |

## Architecture

```
Government/Open Data (CSV/API)
        ↓
   etl/extract.py       — read raw, no interpretation
        ↓
   etl/validate.py      — required fields, plausible lat/lng, date sanity
        ↓
   etl/clean.py          — types, trimming, status normalization
        ↓
   etl/transform.py      — planned_progress (linear model), deviation, priority_score
        ↓
   etl/geospatial.py     — lat/lng -> real GeoPandas geometry
        ↓
   etl/load.py            — upsert into PostGIS, log to project_history
        ↓
   Unified Database (PostgreSQL + PostGIS)
        ↓
   app/ (FastAPI)         — read-only data/analytics API
        ↓
   Chetan's frontend  +  Avinash's AI/risk engine
```

## Data privacy note (Section: Risk mitigation in the SRS)

`citizen_evidence` deliberately has no citizen-identity columns — only
description, photo URL, location, and AI analysis results. Don't add name/
phone/email columns to this table without checking the compliance section
of the SRS first.

## Notes on the AI hook-up

`citizen_evidence.ai_condition`, `ai_issue`, `ai_confidence`, and
`needs_human_review` are populated by Avinash's model. This layer doesn't
call any vision-LLM itself — it just stores the result and exposes it.
`needs_human_review` should be set `TRUE` whenever `ai_confidence` is below
`AI_CONFIDENCE_THRESHOLD` in `.env` (default 0.65), so low-confidence AI
output is flagged in the dashboard rather than shown as fact — per the MVP
checklist requirement.

## Tests

```bash
pytest tests/
```

These hit a real database, so run `init_db.py` + `generate_sample_data.py`
+ `run_etl.py` first.
