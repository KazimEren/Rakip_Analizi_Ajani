-- competitor_analysis_agent schema
-- Fixes a bug in the original CLAUDE.md spec: gen_random_code() is not a
-- real Postgres function. gen_random_uuid() is built into Postgres 13+
-- core (Supabase ships 15+), so no extension is required.

-- v2: modüler (seçmeli) çalıştırma + tiered içerik iskeleti + geçmiş
-- projeler desteği için genişletildi. Modül seçimine bağlı olarak bir
-- çalıştırma sadece bazı alanları üretebildiğinden coğrafi/fiyat/gap
-- kolonları artık NOT NULL değil (modül çalışmadıysa NULL kalır).
-- project_description ve modules_run, bir projeyi UI'daki "Geçmiş
-- Projelerim" panelinden tekrar bulup sadece içerik iskeleti modülünü
-- yeniden tetikleyebilmek için eklendi.
CREATE TABLE IF NOT EXISTS market_and_gap_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name TEXT NOT NULL,
    project_description TEXT NOT NULL DEFAULT '',
    modules_run JSONB NOT NULL DEFAULT '{}',  -- {market_analysis, pricing, content_skeletons, gap_analysis: bool}
    recommended_continent TEXT,
    top_3_countries JSONB,       -- [{rank, country, rationale, ppp_status}] | NULL (modül çalışmadıysa)
    pricing_matrix JSONB,        -- {min_price, avg_price, max_price, recommended_entry_price, rationale} | NULL
    strategic_value_adds JSONB,  -- [{competitor_weakness, recommended_feature}] | NULL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS viral_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES market_and_gap_analysis(id) ON DELETE CASCADE,
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

-- İçerik Oluşturma Ajanı'nın doğrudan okuyacağı, tutmuş her içerik için
-- üretilen 3 varyasyonlu (Ayna/Hibrit/Özgün) iskeletler.
CREATE TABLE IF NOT EXISTS content_skeletons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES market_and_gap_analysis(id) ON DELETE CASCADE,
    source_viral_content_id UUID REFERENCES viral_contents(id) ON DELETE SET NULL,
    competitor_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    tier_type SMALLINT NOT NULL,   -- 1=Ayna, 2=Hibrit, 3=Özgün
    tier_label TEXT NOT NULL,
    skeleton_data JSONB NOT NULL,  -- {hook, intro, body, cta} temiz JSON
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
