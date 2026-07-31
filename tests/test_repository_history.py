from competitor_analysis_agent.db.repository import LocalJsonRepository
from competitor_analysis_agent.models import ContentSkeleton, MarketAndGapAnalysis, ViralContent


def test_local_json_repository_list_and_get_project(tmp_path):
    repo = LocalJsonRepository(str(tmp_path))
    market = MarketAndGapAnalysis(
        project_name="P1", project_description="desc", modules_run={"market_analysis": True}
    )
    repo.save_market_analysis(market)

    projects = repo.list_projects()
    assert len(projects) == 1
    assert projects[0]["id"] == str(market.id)
    assert projects[0]["project_name"] == "P1"

    project = repo.get_project(str(market.id))
    assert project is not None
    assert project["market_analysis"]["project_name"] == "P1"
    assert project["market_analysis"]["project_description"] == "desc"
    assert project["viral_contents"] == []
    assert project["content_skeletons"] == []

    assert repo.get_project("00000000-0000-0000-0000-000000000000") is None


def test_local_json_repository_accumulates_across_saves(tmp_path):
    """Mirrors SupabaseRepository's insert-only semantics: a scoped re-run of
    the content module (the history panel's "Dinamik Yeni İçerik İskeleti
    Çıkar" button) should add to a project's saved content, not replace it."""
    repo = LocalJsonRepository(str(tmp_path))
    market = MarketAndGapAnalysis(project_name="P1")
    repo.save_market_analysis(market)

    vc1 = ViralContent(
        project_id=market.id,
        competitor_name="A",
        platform="TikTok",
        hook_analysis="h",
        intro_and_problem="i",
        body_and_value="b",
        call_to_action="c",
        overall_summary="s",
    )
    repo.save_viral_contents([vc1])

    vc2 = ViralContent(
        project_id=market.id,
        competitor_name="B",
        platform="Instagram",
        hook_analysis="h2",
        intro_and_problem="i2",
        body_and_value="b2",
        call_to_action="c2",
        overall_summary="s2",
    )
    repo.save_viral_contents([vc2])

    cs1 = ContentSkeleton(
        project_id=market.id,
        source_viral_content_id=vc1.id,
        competitor_name="A",
        platform="TikTok",
        tier_type=1,
        tier_label="Ayna",
        skeleton_data={"hook": "x", "intro": "x", "body": "x", "cta": "x"},
    )
    repo.save_content_skeletons([cs1])

    project = repo.get_project(str(market.id))
    assert len(project["viral_contents"]) == 2
    assert {v["competitor_name"] for v in project["viral_contents"]} == {"A", "B"}
    assert len(project["content_skeletons"]) == 1
    assert project["content_skeletons"][0]["tier_label"] == "Ayna"


def test_local_json_repository_save_with_empty_list_is_a_noop(tmp_path):
    repo = LocalJsonRepository(str(tmp_path))
    market = MarketAndGapAnalysis(project_name="P1")
    repo.save_market_analysis(market)

    repo.save_viral_contents([])
    repo.save_content_skeletons([])

    project = repo.get_project(str(market.id))
    assert project["viral_contents"] == []
    assert project["content_skeletons"] == []


def test_local_json_repository_delete_project_removes_it(tmp_path):
    repo = LocalJsonRepository(str(tmp_path))
    market = MarketAndGapAnalysis(project_name="P1")
    repo.save_market_analysis(market)

    assert repo.get_project(str(market.id)) is not None
    assert any(p["id"] == str(market.id) for p in repo.list_projects())

    deleted = repo.delete_project(str(market.id))

    assert deleted is True
    assert repo.get_project(str(market.id)) is None
    assert not any(p["id"] == str(market.id) for p in repo.list_projects())


def test_local_json_repository_delete_unknown_project_returns_false(tmp_path):
    repo = LocalJsonRepository(str(tmp_path))

    assert repo.delete_project("00000000-0000-0000-0000-000000000000") is False


def test_local_json_repository_delete_only_removes_the_targeted_project(tmp_path):
    repo = LocalJsonRepository(str(tmp_path))
    market1 = MarketAndGapAnalysis(project_name="P1")
    market2 = MarketAndGapAnalysis(project_name="P2")
    repo.save_market_analysis(market1)
    repo.save_market_analysis(market2)

    repo.delete_project(str(market1.id))

    assert repo.get_project(str(market1.id)) is None
    assert repo.get_project(str(market2.id)) is not None
    remaining_ids = {p["id"] for p in repo.list_projects()}
    assert remaining_ids == {str(market2.id)}
