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
from competitor_analysis_agent.gui.job_manager import job_manager

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Rakip ve Pazar Analizi Ajanı")


class AnalyzeRequest(BaseModel):
    project_description: str = Field(min_length=1)
    project_name: str | None = None
    mode: Literal["dry_run", "live"] = "dry_run"
    max_competitors: int | None = Field(default=None, ge=1, le=50)


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> JSONResponse:
    if job_manager.is_running():
        raise HTTPException(status_code=409, detail="Zaten çalışan bir analiz var.")

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
    job = job_manager.current
    if job is None or job.result is None:
        return JSONResponse({"available": False})
    return JSONResponse({"available": True, "project_name": job.project_name, **job.result})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
