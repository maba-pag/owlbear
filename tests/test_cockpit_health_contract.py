"""Assembled Cockpit workspace-health contract tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


def _client(monkeypatch, tmp_path: Path, engine: object, memory: object) -> TestClient:
    from owlbear_cockpit import main

    ideas_path = tmp_path / "ideas.md"
    app = main.app
    monkeypatch.setitem(app.dependency_overrides, main._get_health_engine, lambda: engine)
    monkeypatch.setitem(app.dependency_overrides, main._get_health_memory_engine, lambda: memory)
    monkeypatch.setitem(app.dependency_overrides, main._get_health_ideas_path, lambda: ideas_path)
    monkeypatch.setitem(app.dependency_overrides, main.get_engine, lambda: engine)
    monkeypatch.setitem(app.dependency_overrides, main.get_memory_engine, lambda: memory)
    monkeypatch.setitem(app.dependency_overrides, main.get_ideas_path, lambda: ideas_path)
    monkeypatch.setattr(main, "get_engine", lambda: engine)
    monkeypatch.setattr(main, "get_memory_engine", lambda: memory)
    monkeypatch.setattr(main, "get_ideas_path", lambda: ideas_path)
    return TestClient(main.app, raise_server_exceptions=False)


def _engine() -> SimpleNamespace:
    def healthy() -> SimpleNamespace:
        return SimpleNamespace(findings=[], checked_paths=["tasks"])

    return SimpleNamespace(
        task_health=healthy,
        request_health=healthy,
        repair_storage=lambda: SimpleNamespace(
            status="completed",
            started_at="2026-07-17T10:00:00+00:00",
            completed_at="2026-07-17T10:00:01+00:00",
            removed_count=1,
            moved_count=0,
            quarantined_count=0,
            skipped_count=0,
            failed_count=0,
            unresolved_count=0,
            outcomes=[],
            unresolved_findings=[],
            task_health_result=None,
        ),
    )


def test_health_contract_is_typed_and_isolates_checker_failures(monkeypatch, tmp_path: Path) -> None:
    engine = _engine()
    engine.request_health = lambda: (_ for _ in ()).throw(RuntimeError("broken requests"))
    client = _client(
        monkeypatch, tmp_path, engine, SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["modules"]["tasks"]["status"] == "healthy"
    assert body["modules"]["requests"]["status"] == "check-failed"


def test_liveness_and_ideas_integrity_do_not_mutate_ideas(monkeypatch, tmp_path: Path) -> None:
    ideas_path = tmp_path / "ideas.md"
    ideas_path.write_bytes(b"ideas")
    client = _client(
        monkeypatch, tmp_path, _engine(), SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    live = client.get("/health/live")
    before = ideas_path.stat()
    ideas = client.get("/health/ideas")
    after = ideas_path.stat()

    assert live.json() == {"status": "ok"}
    assert ideas.json()["status"] == "healthy"
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)


def test_repair_returns_terminal_receipt(monkeypatch, tmp_path: Path) -> None:
    client = _client(
        monkeypatch, tmp_path, _engine(), SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    response = client.post("/health/tasks/repair")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["removed_count"] == 1


def test_health_route_inventory_keeps_explicit_maintenance_only(monkeypatch, tmp_path: Path) -> None:
    from owlbear_cockpit import main

    _client(
        monkeypatch, tmp_path, _engine(), SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )
    routes = set(main.app.openapi()["paths"])

    assert "/health/tasks/repair" in routes
    assert "/api/tasks/sweep" in routes
    assert "/api/tasks/compact-activity" in routes
    assert "/api/tasks/scan" not in routes
    assert "/api/tasks/cleanup" not in routes
