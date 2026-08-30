-- ============================================================
-- CivSight — Data Infrastructure Schema
-- Owner: Nikita (Data Pipeline + Data Backend)
-- Requires PostgreSQL + PostGIS extension
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ------------------------------------------------------------
-- ENUM: project lifecycle status
-- Matches MVP checklist: PLANNED -> ... -> VERIFIED
-- ------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_status') THEN
        CREATE TYPE project_status AS ENUM (
            'PLANNED',
            'IN_PROGRESS',
            'DELAYED',
            'STALLED',
            'COMPLETED',
            'VERIFIED'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'evidence_source') THEN
        CREATE TYPE evidence_source AS ENUM ('GOVERNMENT', 'CITIZEN', 'AI', 'OFFICER');
    END IF;
END$$;

-- ------------------------------------------------------------
-- CORE TABLE: projects
-- One row per infrastructure project (road, school, hospital...)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id                  SERIAL PRIMARY KEY,
    external_ref        TEXT UNIQUE,               -- id from source govt dataset, if any
    name                TEXT NOT NULL,
    description         TEXT,
    category            TEXT NOT NULL,             -- road | school | hospital | water | building ...
    department          TEXT,
    district             TEXT,
    state               TEXT,

    -- Location: single representative point (for map pins / radius queries)
    location            GEOGRAPHY(POINT, 4326) NOT NULL,
    -- Optional full extent (e.g. road alignment) — nullable, used when available
    geom_extent         GEOGRAPHY(GEOMETRY, 4326),

    budget_allocated    NUMERIC(16, 2),
    budget_spent        NUMERIC(16, 2),

    planned_start        DATE,
    planned_end          DATE,
    planned_progress    NUMERIC(5, 2) DEFAULT 0,   -- 0-100, computed from planned timeline
    actual_progress     NUMERIC(5, 2) DEFAULT 0,   -- 0-100, latest reported/verified value

    current_status      project_status NOT NULL DEFAULT 'PLANNED',
    priority_score       NUMERIC(6, 2),             -- computed by AI/risk engine, cached here

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_location ON projects USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (current_status);
CREATE INDEX IF NOT EXISTS idx_projects_district ON projects (district);

-- ------------------------------------------------------------
-- project_history — every status/progress change over time
-- (historical_updates in the spec)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_history (
    id             SERIAL PRIMARY KEY,
    project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status         project_status,
    progress       NUMERIC(5, 2),
    note           TEXT,
    source         evidence_source NOT NULL DEFAULT 'GOVERNMENT',
    recorded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_history_project ON project_history (project_id, recorded_at DESC);

-- ------------------------------------------------------------
-- citizen_evidence — citizen-submitted photo/location/description
-- + AI analysis results attached to it
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS citizen_evidence (
    id                   SERIAL PRIMARY KEY,
    project_id           INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    description          TEXT,
    photo_url            TEXT,
    location             GEOGRAPHY(POINT, 4326) NOT NULL,
    location_verified    BOOLEAN DEFAULT FALSE,

    -- AI output (populated by Avinash's model, consumed/stored here)
    ai_condition         TEXT,               -- e.g. "cracked surface"
    ai_issue              TEXT,               -- e.g. "construction stopped"
    ai_confidence         NUMERIC(4, 3),       -- 0.000 - 1.000
    needs_human_review    BOOLEAN DEFAULT TRUE, -- flips to FALSE only above confidence threshold

    -- privacy: we deliberately do NOT store citizen identity fields here.
    submitted_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_location ON citizen_evidence USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_evidence_project ON citizen_evidence (project_id);

-- ------------------------------------------------------------
-- facilities — critical facilities used for connectivity impact
-- (schools, hospitals, transport, water, government buildings)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facilities (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,   -- school | hospital | transport | water | government
    location    GEOGRAPHY(POINT, 4326) NOT NULL,
    district    TEXT
);

CREATE INDEX IF NOT EXISTS idx_facilities_location ON facilities USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities (type);

-- ------------------------------------------------------------
-- district_population — population + GIS boundary per district
-- used for "nearby population" style estimates when no fine-grained
-- census grid is available
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS district_population (
    id             SERIAL PRIMARY KEY,
    district       TEXT NOT NULL UNIQUE,
    state          TEXT,
    population      BIGINT,
    boundary       GEOGRAPHY(MULTIPOLYGON, 4326),
    area_sq_km     NUMERIC(10, 2)
);

CREATE INDEX IF NOT EXISTS idx_district_boundary ON district_population USING GIST (boundary);

-- ------------------------------------------------------------
-- infrastructure_network — roads / linear infra used for
-- connectivity analysis (e.g. "road delayed -> hospital access affected")
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS infrastructure_network (
    id          SERIAL PRIMARY KEY,
    name        TEXT,
    type        TEXT,   -- road | rail | water_line | power_line
    geom        GEOGRAPHY(LINESTRING, 4326) NOT NULL,
    district    TEXT
);

CREATE INDEX IF NOT EXISTS idx_network_geom ON infrastructure_network USING GIST (geom);

-- ------------------------------------------------------------
-- Trigger: keep updated_at fresh on projects
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
