# CivicSight — Civic Infrastructure Intelligence Platform

> **CivicSight** combines government and publicly available infrastructure data with citizen-generated ground-level evidence to monitor civic issues, detect underutilized or potentially abandoned public infrastructure, verify resolutions, and recommend where infrastructure should be **repaired**, **repurposed**, or **newly developed**.

---

## 🏛️ How the Whole Thing Fits Together

```
   Existing / Available Data                          Citizen-Contributed Data
 ┌──────────────────────────────────────┐            ┌──────────────────────────────────────┐
 │ • Government infrastructure records  │            │ • Geotagged photos & videos          │
 │ • Open government datasets           │            │ • Precise GPS coordinates            │
 │ • GIS/geospatial road & network data │            │ • Issue description & facility state │
 │ • Population & demographic census    │            │ • "This facility hasn't functioned"  │
 │ • Facility locations & capacities    │            │ • "This school is abandoned"         │
 │ • Public satellite imagery basemap   │            │ • "This toilet is locked"            │
 │ • Historical maintenance records     │            │ • "This water point hasn't worked"   │
 └──────────────────┬───────────────────┘            └──────────────────┬───────────────────┘
                    │                                                   │
                    └─────────────────► 🤖 AI ENGINE ◄──────────────────┘
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
                 🔧 REPAIR               🔄 REPURPOSE            🏗️ NEWLY DEVELOP
            Restore defunct water,     Convert abandoned      Build in deficit zones
            locked public toilets,     schools to clinics     identified by demographic
            and damaged roads          or skill libraries     catchment analysis
```

---

## 🌟 Key Platform Features

### 1. Multi-Layer GIS & Satellite Map
- Interactive Leaflet.js geospatial canvas with real-time toggle between **Vector Streets (OpenStreetMap)** and **High-Resolution Satellite Imagery (Esri World Imagery)**.
- Filter layers by asset type: **Schools (🏫)**, **Public Sanitation/Toilets (🚾)**, **Water Plants (💧)**, **Health Sub-Centers (🏥)**, and **Citizen Ground Alerts (⚠️)**.
- Interactive popups display catchment population, inspection records, and abandonment risk scores.

### 2. Infrastructure Underutilization & Abandonment Detector
- Cross-references official government status with ground citizen feedback and inspection lapses.
- Computes an **Abandonment Score (0–100%)** based on NLP analysis of ground reports, visual deterioration markers (rust, overgrown vegetation, locked chains), and audit delays.

### 3. AI Strategic Recommendation Engine
- **REPAIR**: Identifies critical sanitation or water points where immediate low-cost interventions solve acute community deprivation.
- **REPURPOSE**: Evaluates structurally sound buildings (e.g. consolidated primary schools, vacant agro-godowns) and recommends conversion into Primary Health Sub-Centers, Anganwadi child care, or IT skill centers.
- **NEWLY DEVELOP**: Detects infrastructure deficit hot-spots where dense populations lack public amenities within walking distance (e.g. 13,800 residents with zero functional toilets).

### 4. Citizen Ground Evidence Portal
- One-tap category pills:
  - 🚾 *This toilet is locked*
  - 🏫 *This school is abandoned*
  - 💧 *This water facility hasn't worked for months*
  - ⚠️ *This facility hasn't been functioning*
  - 🚧 *Damaged road / culvert*
- Automatic GPS lock and proximity matching to the nearest registered public asset.
- Photo and video uploads with simulated and live Vision AI evaluation.

### 5. Resolution Verification Studio
- Compares **Before vs. After** photographs for completed public works.
- Generates an AI Visual Verification Score (0–100%) ensuring issues are authentically resolved before closing tickets.

---

## 🏗️ Architecture & Services

| Service | Technology | Port | Responsibilities |
|---|---|---|---|
| **Frontend SPA** | Vanilla JS (ES Modules) + Leaflet.js | `8080` / Static | Interactive GIS map, citizen reporter, abandonment detector, AI recommendation boards |
| **Node.js Express API** | Node.js, Express, Mongoose | `5000` | Auth, Facility CRUD, Citizen Ground Reports, Recommendations, Resolution signoffs |
| **AI Intelligence Service** | Python 3.11+, FastAPI, Pydantic | `8001` | Vision analysis, Abandonment detection, Resolution verification, Recommendation synthesis |
| **Data Backend & ETL** | FastAPI, PostGIS, SQLAlchemy | `8000` | Geospatial network pipelines, Census demographics, PMGSY/JJM dataset ingestion |

---

## 🚀 Running Locally

### 1. Launch the Frontend
Open `frontpage.html` in any modern web browser or serve via:
```bash
npx serve .
# or
python -m http.server 8080
```

### 2. Run the Express Node API
```bash
npm install
npm run dev
# Server running at http://localhost:5000
```

### 3. Run the AI Intelligence Service
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
# Swagger docs at http://localhost:8001/docs
```

---

## 📡 API Endpoints Summary

### Express API (`:5000`)
- `GET /api/facilities` — List government assets with filter by district, type, status, and abandonment risk.
- `POST /api/facilities` — Register new public infrastructure asset (Officer/Admin).
- `GET /api/civic-reports` — List ground citizen evidence reports.
- `POST /api/civic-reports` — Submit geotagged citizen ground report.
- `PATCH /api/civic-reports/:id/verify` — Submit resolution verification with before/after evidence.
- `GET /api/recommendations` — Fetch AI strategic recommendations (Repair, Repurpose, Develop).
- `PATCH /api/recommendations/:id/status` — Approve or update recommendation status.

### FastAPI AI Service (`:8001`)
- `POST /ai/detect-abandonment` — Calculate abandonment score and extract risk signals.
- `POST /ai/recommend-action` — Synthesize condition + demographics into Repair/Repurpose/Develop plan.
- `POST /ai/analyze-image` — Vision model inspection for rust, vegetation, locked gates, structural damage.
- `POST /ai/verify-resolution` — Before-and-after visual resolution verification.
