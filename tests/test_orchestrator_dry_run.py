import json
from pathlib import Path

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.orchestrator import run_pipeline

MARKET_FIELDS = [
    "id",
    "project_name",
    "recommended_continent",
    "top_3_countries",
    "pricing_matrix",
    "strategic_value_adds",
    "created_at",
]

VIRAL_FIELDS = [
    "id",
    "competitor_name",
    "content_url",
    "platform",
    "hook_analysis",
    "intro_and_problem",
    "body_and_value",
    "call_to_action",
    "overall_summary",
    "created_at",
]


def test_full_pipeline_dry_run_writes_schema_valid_output(tmp_path):
    settings = Settings(output_dir=str(tmp_path / "output"))

    market_analysis, viral_contents = run_pipeline(
        project_description="AI destekli kişisel bütçe ve tasarruf uygulaması",
        project_name="TestProject",
        settings=settings,
        dry_run=True,
    )

    assert market_analysis.project_name == "TestProject"
    assert market_analysis.recommended_continent
    assert len(market_analysis.top_3_countries) == 3
    pm = market_analysis.pricing_matrix
    assert pm.min_price <= pm.avg_price <= pm.max_price
    assert len(market_analysis.strategic_value_adds) >= 1
    assert len(viral_contents) >= 1

    market_json_path = Path(settings.output_dir) / "market_and_gap_analysis.json"
    viral_json_path = Path(settings.output_dir) / "viral_contents.json"
    assert market_json_path.exists()
    assert viral_json_path.exists()

    market_row = json.loads(market_json_path.read_text(encoding="utf-8"))
    for field in MARKET_FIELDS:
        assert field in market_row

    viral_rows = json.loads(viral_json_path.read_text(encoding="utf-8"))
    assert isinstance(viral_rows, list)
    assert len(viral_rows) >= 1
    for row in viral_rows:
        for field in VIRAL_FIELDS:
            assert field in row
