"""Assembled Cockpit workspace-health contract tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import TaskHealthFinding, TaskHealthResult


_CONFIG = """\
statuses: [shape, build, verify, collect]
priorities: [low, medium, high]
claim_timeout: 1h
next_id: 2
entry_status: shape
terminal_status: collect
agent_map: {shape: shaper, build: builder, verify: verifier, collect: collector}
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _real_engine(tmp_path: Path) -> tuple[KanbanEngine, Path]:
    board = tmp_path / "board"
    (board / "tasks").mkdir(parents=True)
    (board / "archive").mkdir()
    (board / "config.yml").write_text(_CONFIG, encoding="utf-8")
    source = board / "tasks" / "1-archived-drift.md"
    source.write_text(
        """---
id: 1
title: Archived drift
status: archived
priority: medium
created: '2026-07-17T00:00:00+00:00'
updated: '2026-07-17T00:00:00+00:00'
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: completed
archival_refs: []
---

body
""",
        encoding="utf-8",
    )
    return KanbanEngine(board, activity_log=False), source


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


def test_task_health_projection_preserves_repairability_and_severity(monkeypatch, tmp_path: Path) -> None:
    engine = _engine()
    repairable = [
        TaskHealthFinding(code=f"REPAIRABLE_{index}", detail="repairable", repairable=True) for index in range(2)
    ]
    engine.task_health = lambda: TaskHealthResult(findings=repairable, repairable_count=2)
    client = _client(
        monkeypatch, tmp_path, engine, SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    aggregate = client.get("/health")
    focused = client.get("/health/tasks")

    assert aggregate.json()["status"] == "attention"
    for response in (aggregate, focused):
        task_health = response.json()["modules"]["tasks"] if response is aggregate else response.json()
        assert task_health["status"] == "attention"
        assert task_health["repairable_count"] == 2
        assert len(task_health["findings"]) == 2

    unresolved = TaskHealthFinding(code="UNRESOLVED", detail="manual repair", repairable=False)
    engine.task_health = lambda: TaskHealthResult(
        findings=[*repairable, unresolved],
        repairable_count=2,
    )

    mixed_aggregate = client.get("/health")
    mixed_focused = client.get("/health/tasks")

    for response in (mixed_aggregate, mixed_focused):
        task_health = response.json()["modules"]["tasks"] if response is mixed_aggregate else response.json()
        assert task_health["status"] == "unhealthy"
        assert task_health["repairable_count"] == 2
        assert len(task_health["findings"]) == 3


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


def test_repair_uses_real_deterministic_engine_contract(monkeypatch, tmp_path: Path) -> None:
    engine, source = _real_engine(tmp_path)
    monkeypatch.setattr(engine, "repair_storage", lambda: pytest.fail("legacy repair workflow invoked"))
    client = _client(
        monkeypatch, tmp_path, engine, SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    response = client.post("/health/tasks/repair")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["started_at"] <= body["completed_at"]
    assert body["removed_count"] == 0
    assert body["moved_count"] == 1
    assert body["quarantined_count"] == 0
    assert body["skipped_count"] == 0
    assert body["failed_count"] == 0
    assert body["unresolved_count"] == 0
    assert body["outcomes"][0]["action"] == "moved"
    assert body["unresolved_findings"] == []
    assert body["task_health_result"]["findings"] == []
    assert not source.exists()
    assert (engine.kanban_dir / "archive" / source.name).exists()


def test_repair_receipt_uses_full_post_repair_graph_health(monkeypatch, tmp_path: Path) -> None:
    engine, _source = _real_engine(tmp_path)
    unresolved_source = engine.tasks_dir / "2-missing-dependency.md"
    unresolved_source.write_text(
        """---
id: 2
title: Missing dependency
status: shape
priority: medium
created: '2026-07-17T00:00:00+00:00'
updated: '2026-07-17T00:00:00+00:00'
tags: []
parent: null
depends_on: [999]
blocked: false
block_reason: null
claimed_at: null
---

body
""",
        encoding="utf-8",
    )
    client = _client(
        monkeypatch, tmp_path, engine, SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    response = client.post("/health/tasks/repair")

    assert response.status_code == 200
    body = response.json()
    assert body["moved_count"] == 1
    assert body["unresolved_count"] == 1
    assert [finding["code"] for finding in body["unresolved_findings"]] == ["MISSING_DEPENDENCY"]
    assert [finding["code"] for finding in body["task_health_result"]["findings"]] == ["MISSING_DEPENDENCY"]
    assert client.get("/health").json()["modules"]["tasks"]["findings"] == body["task_health_result"]["findings"]


def test_repair_failure_returns_no_receipt(monkeypatch, tmp_path: Path) -> None:
    from owlbear_cockpit import main

    engine = SimpleNamespace(kanban_dir=tmp_path, board_config=lambda: "config")
    monkeypatch.setattr(main, "repair_task_storage", lambda *_: (_ for _ in ()).throw(RuntimeError("repair failed")))
    client = _client(
        monkeypatch, tmp_path, engine, SimpleNamespace(health=lambda: SimpleNamespace(findings=[], checked_paths=[]))
    )

    response = client.post("/health/tasks/repair")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "COCKPIT_INTERNAL_ERROR"
    assert "status" not in body
    assert "completed_at" not in body
    assert "task_health_result" not in body


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
