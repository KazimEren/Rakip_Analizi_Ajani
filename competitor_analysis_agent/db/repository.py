from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.models import ContentSkeleton, MarketAndGapAnalysis, ViralContent

_PROJECT_SUMMARY_FIELDS = ["id", "project_name", "recommended_continent", "modules_run", "created_at"]


class Repository(Protocol):
    def save_market_analysis(self, record: MarketAndGapAnalysis) -> None: ...

    def save_viral_contents(self, records: list[ViralContent]) -> None: ...

    def save_content_skeletons(self, records: list[ContentSkeleton]) -> None: ...

    def list_projects(self) -> list[dict]: ...

    def get_project(self, project_id: str) -> dict | None: ...


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

    def save_content_skeletons(self, records: list[ContentSkeleton]) -> None:
        if not records:
            return
        rows = [r.to_supabase_row() for r in records]
        self._client.table("content_skeletons").insert(rows).execute()

    def list_projects(self) -> list[dict]:
        response = (
            self._client.table("market_and_gap_analysis")
            .select(",".join(_PROJECT_SUMMARY_FIELDS))
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def get_project(self, project_id: str) -> dict | None:
        market_response = (
            self._client.table("market_and_gap_analysis").select("*").eq("id", project_id).execute()
        )
        if not market_response.data:
            return None
        viral_response = self._client.table("viral_contents").select("*").eq("project_id", project_id).execute()
        skeleton_response = (
            self._client.table("content_skeletons").select("*").eq("project_id", project_id).execute()
        )
        return {
            "market_analysis": market_response.data[0],
            "viral_contents": viral_response.data or [],
            "content_skeletons": skeleton_response.data or [],
        }


class LocalJsonRepository:
    """Dry-run stand-in: writes the exact same row shape SupabaseRepository
    would insert, one file per project (./output/projects/<id>.json), so the
    "Geçmiş Projelerim" history panel and scoped re-runs can be exercised and
    verified end-to-end in dry-run mode too, without real credentials."""

    def __init__(self, output_dir: str = "output") -> None:
        self._dir = Path(output_dir)
        self._projects_dir = self._dir / "projects"
        self._projects_dir.mkdir(parents=True, exist_ok=True)

    def _project_path(self, project_id) -> Path:
        return self._projects_dir / f"{project_id}.json"

    def _read_project(self, project_id) -> dict:
        path = self._project_path(project_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"market_analysis": None, "viral_contents": [], "content_skeletons": []}

    def _write_project(self, project_id, data: dict) -> None:
        self._project_path(project_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def save_market_analysis(self, record: MarketAndGapAnalysis) -> None:
        data = self._read_project(record.id)
        data["market_analysis"] = record.to_supabase_row()
        self._write_project(record.id, data)

    def save_viral_contents(self, records: list[ViralContent]) -> None:
        if not records:
            return
        project_id = records[0].project_id
        data = self._read_project(project_id)
        # Appends rather than replaces, mirroring SupabaseRepository's
        # insert-only semantics -- a re-trigger of the content module
        # (see "Dinamik Yeni İçerik İskeleti Çıkar") adds to a project's
        # history instead of discarding what was generated before.
        data["viral_contents"] = data.get("viral_contents", []) + [r.to_supabase_row() for r in records]
        self._write_project(project_id, data)

    def save_content_skeletons(self, records: list[ContentSkeleton]) -> None:
        if not records:
            return
        project_id = records[0].project_id
        data = self._read_project(project_id)
        data["content_skeletons"] = data.get("content_skeletons", []) + [r.to_supabase_row() for r in records]
        self._write_project(project_id, data)

    def list_projects(self) -> list[dict]:
        projects: list[dict] = []
        for path in self._projects_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            market = data.get("market_analysis")
            if not market:
                continue
            projects.append({field: market.get(field) for field in _PROJECT_SUMMARY_FIELDS})
        projects.sort(key=lambda p: p.get("created_at") or "", reverse=True)
        return projects

    def get_project(self, project_id: str) -> dict | None:
        path = self._project_path(project_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


def get_repository(settings: Settings, dry_run: bool) -> Repository:
    if dry_run:
        return LocalJsonRepository(settings.output_dir)
    return SupabaseRepository(settings)
