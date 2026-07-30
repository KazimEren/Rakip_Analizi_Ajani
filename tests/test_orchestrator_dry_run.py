from pathlib import Path

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.db.repository import LocalJsonRepository
from competitor_analysis_agent.orchestrator import run_pipeline

MARKET_FIELDS = [
    "id",
    "project_name",
    "project_description",
    "modules_run",
    "recommended_continent",
    "top_3_countries",
    "pricing_matrix",
    "strategic_value_adds",
    "created_at",
]

VIRAL_FIELDS = [
    "id",
    "project_id",
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

SKELETON_FIELDS = [
    "id",
    "project_id",
    "source_viral_content_id",
    "competitor_name",
    "platform",
    "tier_type",
    "tier_label",
    "skeleton_data",
    "status",
    "created_at",
]


def test_full_pipeline_dry_run_writes_schema_valid_output(tmp_path):
    settings = Settings(output_dir=str(tmp_path / "output"))

    market_analysis, viral_contents, content_skeletons = run_pipeline(
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
    # 3 tier (Ayna/Hibrit/Özgün) per selected content item.
    assert len(content_skeletons) == len(viral_contents) * 3
    assert all(vc.project_id == market_analysis.id for vc in viral_contents)
    assert all(cs.project_id == market_analysis.id for cs in content_skeletons)

    project_json_path = Path(settings.output_dir) / "projects" / f"{market_analysis.id}.json"
    assert project_json_path.exists()

    repository = LocalJsonRepository(settings.output_dir)
    project = repository.get_project(str(market_analysis.id))
    assert project is not None

    market_row = project["market_analysis"]
    for field in MARKET_FIELDS:
        assert field in market_row

    viral_rows = project["viral_contents"]
    assert isinstance(viral_rows, list)
    assert len(viral_rows) >= 1
    for row in viral_rows:
        for field in VIRAL_FIELDS:
            assert field in row

    skeleton_rows = project["content_skeletons"]
    assert isinstance(skeleton_rows, list)
    assert len(skeleton_rows) == len(viral_rows) * 3
    for row in skeleton_rows:
        for field in SKELETON_FIELDS:
            assert field in row

    projects = repository.list_projects()
    assert any(p["id"] == str(market_analysis.id) for p in projects)
