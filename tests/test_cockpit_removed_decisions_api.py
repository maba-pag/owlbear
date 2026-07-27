"""Retired Cockpit task-decision routes remain absent."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from owlbear_kanban import NativeWorkspace

from owlbear_cockpit.deps import get_workspace
from owlbear_cockpit.main import app


def test_retired_decision_routes_return_not_found(tmp_path: Path) -> None:
    work_root = tmp_path / ".owlbear" / "kanban"
    work_root.mkdir(parents=True)
    app.dependency_overrides[get_workspace] = lambda: NativeWorkspace(work_root)
    try:
        with TestClient(app) as client:
            assert client.get("/api/decisions/pending").status_code == 404
            assert client.post("/api/decisions/1/resolve", json={}).status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_retired_decision_route_module_is_absent(project_root: Path) -> None:
    path = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "routes" / "decisions.py"
    assert not path.exists()
