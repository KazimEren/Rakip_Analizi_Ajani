"""Tests for the content-skeleton pipeline's de-dup behavior: a viral post
whose content_url is already saved as a source_post_url in content_skeletons
must be skipped before it's re-scraped/re-analyzed (no wasted LLM calls, no
duplicate rows)."""

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.llm.gemini_client import MockLLMClient
from competitor_analysis_agent.orchestrator import run_content_module, run_pipeline
from competitor_analysis_agent.scraping.fixtures import MOCK_COMPETITORS, MOCK_CONTENT
from competitor_analysis_agent.scraping.scraper import MockScraper


class _FakeRepository:
    def __init__(self, existing_urls: set[str]):
        self._existing_urls = existing_urls

    def get_existing_source_post_urls(self) -> set[str]:
        return self._existing_urls


def test_run_content_module_skips_items_with_already_saved_source_post_url():
    llm = MockLLMClient()
    scraper = MockScraper()
    already_analyzed = {MOCK_CONTENT[0].content_url}
    repository = _FakeRepository(already_analyzed)

    viral_contents, content_skeletons = run_content_module(
        llm, scraper, MOCK_COMPETITORS, count=3, repository=repository
    )

    assert len(viral_contents) == 1
    assert viral_contents[0].competitor_name == MOCK_CONTENT[1].competitor_name
    assert len(content_skeletons) == 3
    assert all(cs.source_post_url == MOCK_CONTENT[1].content_url for cs in content_skeletons)


def test_run_content_module_skips_nothing_when_repository_has_no_existing_urls():
    llm = MockLLMClient()
    scraper = MockScraper()
    repository = _FakeRepository(set())

    viral_contents, content_skeletons = run_content_module(
        llm, scraper, MOCK_COMPETITORS, count=3, repository=repository
    )

    assert len(viral_contents) == len(MOCK_CONTENT)
    assert len(content_skeletons) == len(MOCK_CONTENT) * 3


def test_run_content_module_processes_all_items_when_no_repository_given():
    """repository is optional -- callers that don't pass one (e.g. isolated
    unit tests) get the pre-existing, no-de-dup behavior."""
    llm = MockLLMClient()
    scraper = MockScraper()

    viral_contents, content_skeletons = run_content_module(llm, scraper, MOCK_COMPETITORS, count=3)

    assert len(viral_contents) == len(MOCK_CONTENT)
    assert len(content_skeletons) == len(MOCK_CONTENT) * 3


def test_run_pipeline_second_run_skips_previously_analyzed_content(tmp_path):
    """End-to-end: running the full dry-run pipeline twice against the same
    output_dir must not re-tier a source post the first run already saved."""
    settings = Settings(output_dir=str(tmp_path / "output"))
    modules = {
        "market_analysis": False,
        "pricing": False,
        "content_skeletons": True,
        "gap_analysis": False,
    }

    _, first_viral, first_skeletons = run_pipeline(
        project_description="AI destekli kişisel bütçe uygulaması",
        project_name="Run1",
        settings=settings,
        dry_run=True,
        modules=modules,
        content_skeleton_count=len(MOCK_CONTENT),
    )
    assert len(first_viral) == len(MOCK_CONTENT)
    assert len(first_skeletons) == len(MOCK_CONTENT) * 3

    _, second_viral, second_skeletons = run_pipeline(
        project_description="AI destekli kişisel bütçe uygulaması",
        project_name="Run2",
        settings=settings,
        dry_run=True,
        modules=modules,
        content_skeleton_count=len(MOCK_CONTENT),
    )

    assert second_viral == []
    assert second_skeletons == []
