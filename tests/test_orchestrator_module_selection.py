import pytest

import competitor_analysis_agent.orchestrator as orchestrator_module
from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.llm.gemini_client import MockLLMClient
from competitor_analysis_agent.models import RawContentItem
from competitor_analysis_agent.orchestrator import run_pipeline, select_top_performing_content
from competitor_analysis_agent.scraping.fixtures import MOCK_COMPETITORS, MOCK_COMPLAINTS, MOCK_CONTENT, MOCK_PRICING


class _SpyScraper:
    """Records which scraping methods were actually invoked, backed by the
    same canned fixtures MockScraper uses -- lets a test assert that an
    unselected module never triggers its scraping call at all."""

    def __init__(self):
        self.calls: list[str] = []

    def search_competitors(self, keywords):
        self.calls.append("search_competitors")
        return list(MOCK_COMPETITORS)

    def scrape_reviews(self, competitor):
        self.calls.append("scrape_reviews")
        return [c for c in MOCK_COMPLAINTS if c.competitor_name == competitor.name]

    def scrape_pricing(self, competitor):
        self.calls.append("scrape_pricing")
        return [p for p in MOCK_PRICING if p.competitor_name == competitor.name]

    def scrape_social_content(self, competitor, platforms):
        self.calls.append("scrape_social_content")
        return [c for c in MOCK_CONTENT if c.competitor_name == competitor.name and c.platform in platforms]


def _patch_dry_run_factories(monkeypatch, spy_scraper: _SpyScraper) -> None:
    monkeypatch.setattr(orchestrator_module, "get_scraper", lambda settings, dry_run: spy_scraper)
    monkeypatch.setattr(orchestrator_module, "get_llm_client", lambda settings, dry_run: MockLLMClient())


def test_run_pipeline_only_scrapes_for_selected_modules(monkeypatch, tmp_path):
    spy_scraper = _SpyScraper()
    _patch_dry_run_factories(monkeypatch, spy_scraper)
    settings = Settings(output_dir=str(tmp_path / "output"))

    market_analysis, viral_contents, content_skeletons = run_pipeline(
        project_description="AI destekli kişisel bütçe uygulaması",
        project_name="TestProject",
        settings=settings,
        dry_run=True,
        modules={
            "market_analysis": False,
            "pricing": True,
            "content_skeletons": False,
            "gap_analysis": False,
        },
    )

    assert "scrape_pricing" in spy_scraper.calls
    assert "scrape_reviews" not in spy_scraper.calls
    assert "scrape_social_content" not in spy_scraper.calls

    assert market_analysis.recommended_continent is None
    assert market_analysis.top_3_countries is None
    assert market_analysis.pricing_matrix is not None
    assert market_analysis.strategic_value_adds is None
    assert viral_contents == []
    assert content_skeletons == []
    assert market_analysis.modules_run == {
        "market_analysis": False,
        "pricing": True,
        "content_skeletons": False,
        "gap_analysis": False,
    }


def test_run_pipeline_content_module_scrapes_social_only(monkeypatch, tmp_path):
    spy_scraper = _SpyScraper()
    _patch_dry_run_factories(monkeypatch, spy_scraper)
    settings = Settings(output_dir=str(tmp_path / "output"))

    market_analysis, viral_contents, content_skeletons = run_pipeline(
        project_description="AI destekli kişisel bütçe uygulaması",
        project_name="TestProject",
        settings=settings,
        dry_run=True,
        modules={
            "market_analysis": False,
            "pricing": False,
            "content_skeletons": True,
            "gap_analysis": False,
        },
        content_skeleton_count=1,
    )

    assert "scrape_social_content" in spy_scraper.calls
    assert "scrape_pricing" not in spy_scraper.calls
    assert "scrape_reviews" not in spy_scraper.calls
    assert market_analysis.pricing_matrix is None
    assert market_analysis.strategic_value_adds is None
    assert len(viral_contents) == 1
    assert len(content_skeletons) == 3
    assert all(vc.project_id == market_analysis.id for vc in viral_contents)
    assert all(cs.project_id == market_analysis.id for cs in content_skeletons)


def test_run_pipeline_raises_when_no_modules_selected(tmp_path):
    settings = Settings(output_dir=str(tmp_path / "output"))

    with pytest.raises(ValueError):
        run_pipeline(
            project_description="x",
            project_name="TestProject",
            settings=settings,
            dry_run=True,
            modules={
                "market_analysis": False,
                "pricing": False,
                "content_skeletons": False,
                "gap_analysis": False,
            },
        )


def test_select_top_performing_content_ranks_by_engagement_descending():
    items = [
        RawContentItem(competitor_name="A", platform="TikTok", engagement_note="engagement=100"),
        RawContentItem(competitor_name="B", platform="TikTok", engagement_note="engagement=5000"),
        RawContentItem(competitor_name="C", platform="TikTok", engagement_note=""),
        RawContentItem(competitor_name="D", platform="TikTok", engagement_note="engagement=900"),
    ]

    top2 = select_top_performing_content(items, count=2)

    assert [i.competitor_name for i in top2] == ["B", "D"]


def test_select_top_performing_content_treats_missing_or_unparseable_engagement_as_zero():
    items = [
        RawContentItem(competitor_name="A", platform="TikTok", engagement_note="not-a-number"),
        RawContentItem(competitor_name="B", platform="TikTok", engagement_note="engagement=10"),
    ]

    top1 = select_top_performing_content(items, count=1)

    assert top1[0].competitor_name == "B"
