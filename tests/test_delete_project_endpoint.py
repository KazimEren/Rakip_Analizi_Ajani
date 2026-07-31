"""Integration test for DELETE /api/projects/{id} through the real FastAPI
app + job_manager, forced into dry-run via env vars so it never touches the
real Supabase/Gemini/Apify credentials this repo's own .env happens to have
configured."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("APIFY_API_TOKEN", "")

    from competitor_analysis_agent.gui.server import app

    return TestClient(app)


def _run_minimal_analysis(client: TestClient) -> str:
    payload = {
        "project_description": "Silme testi için proje",
        "mode": "dry_run",
        "run_market_analysis": True,
        "run_pricing": False,
        "run_content_skeletons": False,
        "run_gap_analysis": False,
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200

    status = None
    for _ in range(50):
        status = client.get("/api/status").json()
        if status["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert status["status"] == "done", status

    return client.get("/api/results").json()["market_analysis"]["id"]


def test_delete_project_removes_it_from_history(client):
    project_id = _run_minimal_analysis(client)

    projects_before = client.get("/api/projects").json()["projects"]
    assert any(p["id"] == project_id for p in projects_before)

    response = client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 200
    assert response.json() == {"deleted": True, "project_id": project_id}

    projects_after = client.get("/api/projects").json()["projects"]
    assert not any(p["id"] == project_id for p in projects_after)

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 404


def test_delete_unknown_project_returns_404(client):
    response = client.delete("/api/projects/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_delete_does_not_affect_other_projects(client):
    project_id_1 = _run_minimal_analysis(client)
    project_id_2 = _run_minimal_analysis(client)

    client.delete(f"/api/projects/{project_id_1}")

    assert client.get(f"/api/projects/{project_id_1}").status_code == 404
    assert client.get(f"/api/projects/{project_id_2}").status_code == 200
