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
    district    TEXT,
    source_ref  TEXT,
    geo_precision TEXT DEFAULT 'source_coordinates'
);

CREATE INDEX IF NOT EXISTS idx_facilities_location ON facilities USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities (type);
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS source_ref TEXT;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS geo_precision TEXT DEFAULT 'source_coordinates';
CREATE UNIQUE INDEX IF NOT EXISTS uq_facilities_type_source_ref
    ON facilities (type, source_ref) WHERE source_ref IS NOT NULL;

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
    source_ref  TEXT,
    name        TEXT,
    type        TEXT,   -- road | rail | water_line | power_line
    geom        GEOGRAPHY(LINESTRING, 4326) NOT NULL,
    district    TEXT,
    length_km   NUMERIC(12, 3),
    status      TEXT,
    geo_precision TEXT DEFAULT 'source_geometry',
    source_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_network_geom ON infrastructure_network USING GIST (geom);
ALTER TABLE infrastructure_network ADD COLUMN IF NOT EXISTS source_ref TEXT;
ALTER TABLE infrastructure_network ADD COLUMN IF NOT EXISTS length_km NUMERIC(12, 3);
ALTER TABLE infrastructure_network ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE infrastructure_network ADD COLUMN IF NOT EXISTS geo_precision TEXT DEFAULT 'source_geometry';
ALTER TABLE infrastructure_network ADD COLUMN IF NOT EXISTS source_metadata JSONB DEFAULT '{}'::jsonb;
CREATE UNIQUE INDEX IF NOT EXISTS uq_network_type_source_ref
    ON infrastructure_network (type, source_ref) WHERE source_ref IS NOT NULL;

-- ------------------------------------------------------------
-- infrastructure_coverage — non-spatial aggregate public data
-- such as state-level PMGSY/JJM files that do not include point
-- or line geometry. These are intentionally not map features.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS infrastructure_coverage (
    id                    SERIAL PRIMARY KEY,
    source                TEXT NOT NULL,
    area_level            TEXT NOT NULL,
    state                 TEXT NOT NULL,
    district              TEXT,
    district_key          TEXT NOT NULL DEFAULT '',
    metric_name           TEXT NOT NULL,
    metric_value          NUMERIC(16, 3),
    secondary_metric_name TEXT,
    secondary_metric_value NUMERIC(16, 3),
    total_households_lakh NUMERIC(16, 3),
    geo_precision         TEXT NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coverage_source_state ON infrastructure_coverage (source, state);
CREATE UNIQUE INDEX IF NOT EXISTS uq_coverage_dataset_area_metric
    ON infrastructure_coverage (source, area_level, state, district_key, metric_name);

-- ------------------------------------------------------------
-- lgd_villages — national-scale LGD village reference table.
-- Loader reads CSV in chunks so 650k+ rows are laptop-safe.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lgd_villages (
    village_code TEXT PRIMARY KEY,
    village_name TEXT NOT NULL,
    state        TEXT,
    district     TEXT,
    block        TEXT,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lgd_villages_lookup ON lgd_villages (state, district, block, village_name);

-- ------------------------------------------------------------
-- schools — synthetic/representative school infrastructure data.
-- Not official UDISE+ records; used for prototype demonstration.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schools (
    id                  SERIAL PRIMARY KEY,
    school_id           TEXT UNIQUE NOT NULL,
    school_name         TEXT NOT NULL,
    state               TEXT NOT NULL,
    district            TEXT NOT NULL,
    block               TEXT,
    village             TEXT,
    location            GEOGRAPHY(POINT, 4326) NOT NULL,
    school_category     TEXT,
    management          TEXT,
    student_count       INTEGER,
    teacher_count       INTEGER,
    classroom_count     INTEGER,
    has_electricity     BOOLEAN DEFAULT TRUE,
    has_drinking_water  BOOLEAN DEFAULT TRUE,
    has_toilet          BOOLEAN DEFAULT TRUE,
    has_girls_toilet    BOOLEAN DEFAULT TRUE,
    has_ramp            BOOLEAN DEFAULT TRUE,
    has_computer        BOOLEAN DEFAULT TRUE,
    has_internet        BOOLEAN DEFAULT TRUE,
    has_library         BOOLEAN DEFAULT TRUE,
    has_playground      BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_schools_location ON schools USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_schools_district ON schools (district);

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
