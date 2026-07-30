"""Local FastAPI app for the desktop GUI.

Wraps the existing, unmodified pipeline (config.get_settings +
orchestrator.run_pipeline) behind a few JSON endpoints so a local static
frontend can drive it. No pipeline/business logic lives in this file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from competitor_analysis_agent.config import get_settings
from competitor_analysis_agent.db.repository import get_repository
from competitor_analysis_agent.gui.job_manager import job_manager

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Rakip ve Pazar Analizi Ajanı")


class AnalyzeRequest(BaseModel):
    project_description: str = Field(min_length=1)
    project_name: str | None = None
    mode: Literal["dry_run", "live"] = "dry_run"
    max_competitors: int | None = Field(default=None, ge=1, le=50)
    # Checkbox 1-4: hangi modüllerin çalışacağı. Varsayılan yok -- frontend
    # her zaman gönderir; en az biri True olmalı (aksi halde 422).
    run_market_analysis: bool
    run_pricing: bool
    run_content_skeletons: bool
    run_gap_analysis: bool
    content_skeleton_count: int = Field(default=3, ge=1, le=10)


class ContentSkeletonRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=10)


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> JSONResponse:
    if job_manager.is_running():
        raise HTTPException(status_code=409, detail="Zaten çalışan bir analiz var.")

    modules = {
        "market_analysis": payload.run_market_analysis,
        "pricing": payload.run_pricing,
        "content_skeletons": payload.run_content_skeletons,
        "gap_analysis": payload.run_gap_analysis,
    }
    if not any(modules.values()):
        raise HTTPException(status_code=422, detail="En az bir modül seçilmelidir.")

    settings = get_settings()
    if payload.max_competitors is not None:
        settings = settings.model_copy(update={"max_competitors_per_search": payload.max_competitors})

    requested_dry_run = True if payload.mode == "dry_run" else False
    dry_run = settings.resolve_dry_run(requested_dry_run)

    project_name = payload.project_name or payload.project_description[:60]

    job = job_manager.start(
        project_description=payload.project_description,
        project_name=project_name,
        settings=settings,
        dry_run=dry_run,
        modules=modules,
        content_skeleton_count=payload.content_skeleton_count,
    )
    return JSONResponse({"job_id": job.id, "dry_run": job.dry_run, "status": job.status})


@app.get("/api/status")
def status() -> JSONResponse:
    job = job_manager.current
    if job is None:
        return JSONResponse({"status": "idle"})
    return JSONResponse(
        {
            "job_id": job.id,
            "status": job.status,
            "kind": job.kind,
            "dry_run": job.dry_run,
            "project_name": job.project_name,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error": job.error,
        }
    )


@app.get("/api/logs")
def logs(since: int = 0) -> JSONResponse:
    job = job_manager.current
    if job is None:
        return JSONResponse({"logs": [], "cursor": since})
    records = job.logs_since(since)
    cursor = records[-1].seq if records else since
    return JSONResponse(
        {
            "logs": [{"seq": r.seq, "ts": r.ts, "level": r.level, "message": r.message} for r in records],
            "cursor": cursor,
        }
    )


@app.get("/api/results")
def results() -> JSONResponse:
    # Only "analyze" jobs produce a market_analysis-shaped result -- a
    # content-skeleton re-trigger job (started from the history panel) has a
    # different result shape and is read via GET /api/projects/{id} instead,
    # so it's deliberately excluded here rather than left to crash the main
    # results panel's renderer.
    job = job_manager.current
    if job is None or job.result is None or job.kind != "analyze":
        return JSONResponse({"available": False})
    return JSONResponse({"available": True, "project_name": job.project_name, **job.result})


@app.get("/api/projects")
def list_projects() -> JSONResponse:
    settings = get_settings()
    dry_run = settings.resolve_dry_run(None)
    repository = get_repository(settings, dry_run)
    return JSONResponse({"projects": repository.list_projects()})


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> JSONResponse:
    settings = get_settings()
    dry_run = settings.resolve_dry_run(None)
    repository = get_repository(settings, dry_run)
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")
    return JSONResponse({"available": True, **project})


@app.post("/api/projects/{project_id}/content-skeletons")
def trigger_content_skeletons(project_id: str, payload: ContentSkeletonRequest) -> JSONResponse:
    if job_manager.is_running():
        raise HTTPException(status_code=409, detail="Zaten çalışan bir analiz var.")

    settings = get_settings()
    dry_run = settings.resolve_dry_run(None)
    repository = get_repository(settings, dry_run)
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    market = project["market_analysis"]
    project_description = market.get("project_description") or ""
    project_name = market.get("project_name") or project_id

    job = job_manager.start_content_skeletons(
        project_id=project_id,
        project_description=project_description,
        project_name=project_name,
        count=payload.count,
        settings=settings,
        dry_run=dry_run,
    )
    return JSONResponse({"job_id": job.id, "dry_run": job.dry_run, "status": job.status})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
