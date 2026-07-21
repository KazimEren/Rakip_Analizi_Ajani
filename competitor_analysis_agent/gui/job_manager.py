"""Runs the existing orchestrator.run_pipeline in a background thread and
exposes its progress/result to the GUI's HTTP layer.

This module does not alter any pipeline logic -- it only wraps the existing
`run_pipeline` call, captures its `logging` output (see the logger.info(...)
calls added to orchestrator.py) into an in-memory queue for the /api/logs
endpoint, and stores the returned result / any exception for /api/results.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any

from competitor_analysis_agent.config import Settings
from competitor_analysis_agent.orchestrator import run_pipeline

_LOG_QUEUE_LOGGER_NAME = "competitor_analysis_agent"


@dataclass
class LogRecord:
    seq: int
    ts: float
    level: str
    message: str


@dataclass
class Job:
    id: str
    status: str = "running"  # running | done | error
    dry_run: bool = True
    project_name: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    _logs: list[LogRecord] = field(default_factory=list, repr=False, compare=False)
    _log_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    _seq: int = field(default=0, compare=False)

    def append_log(self, level: str, message: str) -> None:
        with self._log_lock:
            self._seq += 1
            self._logs.append(LogRecord(seq=self._seq, ts=time.time(), level=level, message=message))

    def logs_since(self, cursor: int) -> list[LogRecord]:
        with self._log_lock:
            return [r for r in self._logs if r.seq > cursor]


class _QueueLogHandler(logging.Handler):
    def __init__(self, job: Job) -> None:
        super().__init__()
        self._job = job

    def emit(self, record: logging.LogRecord) -> None:
        self._job.append_log(record.levelname, self.format(record))


class JobManager:
    """Single-job-at-a-time runner (this is a local single-user desktop
    tool, so a simple mutex is enough -- no need for a job queue)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: Job | None = None

    @property
    def current(self) -> Job | None:
        return self._current

    def is_running(self) -> bool:
        job = self._current
        return job is not None and job.status == "running"

    def start(
        self,
        project_description: str,
        project_name: str,
        settings: Settings,
        dry_run: bool,
    ) -> Job:
        if self.is_running():
            raise RuntimeError("Zaten çalışan bir analiz var. Önce onun bitmesini bekleyin.")

        job = Job(id=str(uuid.uuid4()), dry_run=dry_run, project_name=project_name)
        with self._lock:
            self._current = job

        thread = threading.Thread(
            target=self._run,
            args=(job, project_description, project_name, settings, dry_run),
            daemon=True,
        )
        thread.start()
        return job

    def _run(
        self,
        job: Job,
        project_description: str,
        project_name: str,
        settings: Settings,
        dry_run: bool,
    ) -> None:
        pipeline_logger = logging.getLogger(_LOG_QUEUE_LOGGER_NAME)
        handler = _QueueLogHandler(job)
        handler.setFormatter(logging.Formatter("%(message)s"))
        previous_level = pipeline_logger.level
        pipeline_logger.addHandler(handler)
        pipeline_logger.setLevel(logging.INFO)

        job.append_log("INFO", f"Analiz başlatıldı ({'dry-run' if dry_run else 'live'} mod).")
        try:
            market_analysis, viral_contents = run_pipeline(
                project_description=project_description,
                project_name=project_name,
                settings=settings,
                dry_run=dry_run,
            )
            job.result = {
                "market_analysis": market_analysis.model_dump(mode="json"),
                "viral_contents": [v.model_dump(mode="json") for v in viral_contents],
            }
            job.status = "done"
            job.append_log("INFO", "Analiz başarıyla tamamlandı.")
        except Exception as exc:  # noqa: BLE001 - surfaced to the GUI, not swallowed
            job.error = f"{exc}\n\n{traceback.format_exc()}"
            job.status = "error"
            job.append_log("ERROR", f"Hata: {exc}")
        finally:
            job.finished_at = time.time()
            pipeline_logger.removeHandler(handler)
            pipeline_logger.setLevel(previous_level)


job_manager = JobManager()
