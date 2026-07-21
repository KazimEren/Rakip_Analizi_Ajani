from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.models import MarketAndGapAnalysis, ViralContent


class Repository(Protocol):
    def save_market_analysis(self, record: MarketAndGapAnalysis) -> None: ...

    def save_viral_contents(self, records: list[ViralContent]) -> None: ...


class SupabaseRepository:
    def __init__(self, settings: Settings) -> None:
        from competitor_analysis_agent.db.supabase_client import create_supabase_client

        self._client = create_supabase_client(settings)

    def save_market_analysis(self, record: MarketAndGapAnalysis) -> None:
        self._client.table("market_and_gap_analysis").insert(record.to_supabase_row()).execute()

    def save_viral_contents(self, records: list[ViralContent]) -> None:
        if not records:
            return
        rows = [r.to_supabase_row() for r in records]
        self._client.table("viral_contents").insert(rows).execute()


class LocalJsonRepository:
    """Dry-run stand-in: writes the exact same row shape SupabaseRepository
    would insert, to ./output/*.json, so the pipeline can be exercised and
    verified end-to-end without real credentials."""

    def __init__(self, output_dir: str = "output") -> None:
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save_market_analysis(self, record: MarketAndGapAnalysis) -> None:
        path = self._dir / "market_and_gap_analysis.json"
        path.write_text(json.dumps(record.to_supabase_row(), indent=2, ensure_ascii=False), encoding="utf-8")

    def save_viral_contents(self, records: list[ViralContent]) -> None:
        path = self._dir / "viral_contents.json"
        rows = [r.to_supabase_row() for r in records]
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def get_repository(settings: Settings, dry_run: bool) -> Repository:
    if dry_run:
        return LocalJsonRepository(settings.output_dir)
    return SupabaseRepository(settings)
