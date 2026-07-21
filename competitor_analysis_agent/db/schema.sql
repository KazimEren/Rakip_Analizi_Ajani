-- competitor_analysis_agent schema
-- Fixes a bug in the original CLAUDE.md spec: gen_random_code() is not a
-- real Postgres function. gen_random_uuid() is built into Postgres 13+
-- core (Supabase ships 15+), so no extension is required.

CREATE TABLE IF NOT EXISTS market_and_gap_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name TEXT NOT NULL,
    recommended_continent TEXT NOT NULL,
    top_3_countries JSONB NOT NULL,       -- [{rank, country, rationale, ppp_status}]
    pricing_matrix JSONB NOT NULL,        -- {min_price, avg_price, max_price, recommended_entry_price, rationale}
    strategic_value_adds JSONB NOT NULL,  -- [{competitor_weakness, recommended_feature}]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS viral_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_name TEXT NOT NULL,
    content_url TEXT,
    platform TEXT NOT NULL,          -- "Instagram", "LinkedIn", "YouTube", "TikTok"
    hook_analysis TEXT NOT NULL,     -- 0-3s: ilk dikkat çekme kancası
    intro_and_problem TEXT NOT NULL, -- 3-7s: problemin ortaya koyulması
    body_and_value TEXT NOT NULL,    -- 7-25s: değer önerisi ve ana anlatım
    call_to_action TEXT NOT NULL,    -- 25-30s: kapanış ve eyleme çağrı
    overall_summary TEXT NOT NULL,   -- içeriğin neden tuttuğuna dair genel analiz
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_and_gap_analysis_project_name
    ON market_and_gap_analysis (project_name);

CREATE INDEX IF NOT EXISTS idx_viral_contents_competitor_name
    ON viral_contents (competitor_name);
