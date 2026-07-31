-- Migration for Supabase projects created before the selective-module /
-- content-skeleton-tiering update (see schema.sql for the full, up-to-date
-- shape a fresh install gets via setup_db.py). Safe to run more than once:
-- every statement is additive or relaxes a constraint, never drops a table
-- or column, so no existing data can be lost.
--
-- Run with the same mechanism as setup_db.py (SUPABASE_DB_URL, or paste
-- into the Supabase Dashboard > SQL Editor if that's not set).

ALTER TABLE market_and_gap_analysis
    ADD COLUMN IF NOT EXISTS project_description TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS modules_run JSONB NOT NULL DEFAULT '{}',
    ALTER COLUMN recommended_continent DROP NOT NULL,
    ALTER COLUMN top_3_countries DROP NOT NULL,
    ALTER COLUMN pricing_matrix DROP NOT NULL,
    ALTER COLUMN strategic_value_adds DROP NOT NULL;

ALTER TABLE viral_contents
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES market_and_gap_analysis(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS content_skeletons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES market_and_gap_analysis(id) ON DELETE CASCADE,
    source_viral_content_id UUID REFERENCES viral_contents(id) ON DELETE SET NULL,
    competitor_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    tier_type SMALLINT NOT NULL,
    tier_label TEXT NOT NULL,
    skeleton_data JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_and_gap_analysis_project_name
    ON market_and_gap_analysis (project_name);

CREATE INDEX IF NOT EXISTS idx_viral_contents_competitor_name
    ON viral_contents (competitor_name);

CREATE INDEX IF NOT EXISTS idx_viral_contents_project_id
    ON viral_contents (project_id);

CREATE INDEX IF NOT EXISTS idx_content_skeletons_project_id
    ON content_skeletons (project_id);
