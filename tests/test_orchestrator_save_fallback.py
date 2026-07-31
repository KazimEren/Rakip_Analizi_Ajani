import json

import pytest

import competitor_analysis_agent.orchestrator as orchestrator_module
from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.llm.gemini_client import MockLLMClient
from competitor_analysis_agent.orchestrator import run_pipeline
from competitor_analysis_agent.scraping.scraper import MockScraper

_MARKET_ONLY_MODULES = {
    "market_analysis": True,
    "pricing": False,
    "content_skeletons": False,
    "gap_analysis": False,
}


class _FailingRepository:
    """Simulates an unreachable Supabase project (e.g. DNS resolution
    failure) so the fallback-to-local-backup path can be exercised without
    a real network dependency."""

    def save_market_analysis(self, record):
        raise ConnectionError("getaddrinfo failed")

    def save_viral_contents(self, records):
        raise AssertionError("should not be reached: save_market_analysis already raised")

    def save_content_skeletons(self, records):
        raise AssertionError("should not be reached: save_market_analysis already raised")


def _patch_factories(monkeypatch):
    monkeypatch.setattr(orchestrator_module, "get_scraper", lambda settings, dry_run: MockScraper())
    monkeypatch.setattr(orchestrator_module, "get_llm_client", lambda settings, dry_run: MockLLMClient())
    monkeypatch.setattr(orchestrator_module, "get_repository", lambda settings, dry_run: _FailingRepository())


def test_run_pipeline_backs_up_locally_when_live_db_save_fails(monkeypatch, tmp_path):
    _patch_factories(monkeypatch)
    settings = Settings(output_dir=str(tmp_path / "output"))

    with pytest.raises(ConnectionError):
        run_pipeline(
            project_description="AI destekli fatura uygulaması",
            project_name="TestProject",
            settings=settings,
            dry_run=False,  # live mode -- triggers the fallback path
            modules=_MARKET_ONLY_MODULES,
        )

    backup_files = list((tmp_path / "output" / "projects").glob("*.json"))
    assert len(backup_files) == 1
    backup = json.loads(backup_files[0].read_text(encoding="utf-8"))
    assert backup["market_analysis"]["project_name"] == "TestProject"
    assert backup["market_analysis"]["recommended_continent"]


def test_run_pipeline_does_not_write_fallback_backup_in_dry_run_mode(monkeypatch, tmp_path):
    """dry-run already goes through LocalJsonRepository as the primary
    repository -- the fallback path only matters for a live-mode DB failure,
    so it shouldn't fire (or duplicate anything) here."""
    _patch_factories(monkeypatch)
    settings = Settings(output_dir=str(tmp_path / "output"))

    with pytest.raises(ConnectionError):
        run_pipeline(
            project_description="AI destekli fatura uygulaması",
            project_name="TestProject",
            settings=settings,
            dry_run=True,
            modules=_MARKET_ONLY_MODULES,
        )

    projects_dir = tmp_path / "output" / "projects"
    assert not projects_dir.exists() or not list(projects_dir.glob("*.json"))
