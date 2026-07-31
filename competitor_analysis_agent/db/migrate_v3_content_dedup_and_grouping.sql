-- Migration for Supabase projects created before the content-skeleton
-- de-duplication / concept-grouping / video-generation-tracking update (see
-- schema.sql for the full, up-to-date shape a fresh install gets via
-- setup_db.py). Safe to run more than once, and safe even if
-- migrate_v2_selective_modules.sql was never applied (content_skeletons is
-- created here too if it doesn't exist yet) -- every statement is additive,
-- so no existing data can be lost.
--
-- Run with the same mechanism as setup_db.py (SUPABASE_DB_URL, or paste
-- into the Supabase Dashboard > SQL Editor if that's not set).

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

ALTER TABLE content_skeletons
    ADD COLUMN IF NOT EXISTS source_post_url TEXT,
    ADD COLUMN IF NOT EXISTS concept_group_id UUID,
    ADD COLUMN IF NOT EXISTS concept_summary TEXT,
    ADD COLUMN IF NOT EXISTS video_generated_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS video_generation_count INTEGER NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_skeletons_source_post_url_tier
    ON content_skeletons (source_post_url, tier_type)
    WHERE source_post_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_content_skeletons_concept_group_id
    ON content_skeletons (concept_group_id);

CREATE INDEX IF NOT EXISTS idx_content_skeletons_project_id
    ON content_skeletons (project_id);
