"""Public Cockpit proof for native SSE and read-only legacy inventory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from owlbear_kanban import NativeWorkspace, create_legacy_snapshot

from owlbear_cockpit.deps import get_workspace
from owlbear_cockpit.main import app
from owlbear_cockpit.routes.events import _batch_resources, _build_watch_filter


@pytest.fixture
def workspace(tmp_path: Path) -> NativeWorkspace:
    work_root = tmp_path / ".owlbear" / "kanban"
    work_root.mkdir(parents=True)
    return NativeWorkspace(work_root)


def _store_state(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(sorted((str(path.relative_to(root)), path.read_bytes()) for path in root.rglob("*") if path.is_file()))


def test_native_batch_classification_is_sorted_and_suppresses_legacy_noise(tmp_path: Path) -> None:
    ops_root = tmp_path / ".owlbear"
    changes_root = ops_root / "changes"
    work_root = ops_root / "kanban"
    changes = {
        (1, str(work_root / "jobs" / "1.yaml")),
        (2, str(work_root / "attempts" / "attempt-1" / "2.json")),
        (3, str(changes_root / "change-a" / "delivery" / "nodes.yaml")),
        (4, str(changes_root / "change-a" / "receipts" / "build-1.yaml")),
        (5, str(work_root / "tasks" / "legacy.md")),
        (6, str(work_root / "jobs" / ".tmp-job.yaml")),
        (7, str(changes_root / ".storage.lock")),
    }

    assert _batch_resources(changes, changes_root, work_root) == (
        "attempts",
        "changes",
        "jobs",
        "receipts",
    )
    watch_filter = _build_watch_filter(changes_root, work_root)
    assert watch_filter(None, str(work_root / "jobs" / "1.yaml")) is True
    assert watch_filter(None, str(work_root / "tasks" / "legacy.md")) is False
    assert watch_filter(None, str(work_root / "jobs" / ".tmp-job.yaml")) is False


@pytest.mark.asyncio
async def test_events_stream_one_native_event_per_batch_with_monotonic_tokens(
    workspace: NativeWorkspace,
) -> None:
    work_root = workspace.work_root
    changes_root = work_root.parent / "changes"
    changes_root.mkdir()
    batches = (
        {
            (1, str(work_root / "jobs" / "1.yaml")),
            (2, str(changes_root / "change-a" / "receipts" / "build-1.yaml")),
        },
        {
            (3, str(work_root / "requests" / "pending" / "request-1.yaml")),
            (4, str(work_root / "archive" / "legacy.md")),
        },
    )

    async def _batches(*_args: object, **_kwargs: object):
        for batch in batches:
            yield batch

    app.dependency_overrides[get_workspace] = lambda: workspace
    try:
        with (
            patch("owlbear_cockpit.routes.events.awatch", _batches),
            patch("owlbear_cockpit.routes.events.time.time_ns", return_value=100),
        ):
            transport = httpx.ASGITransport(app=app)
            async with (
                httpx.AsyncClient(transport=transport, base_url="http://test") as client,
                client.stream("GET", "/api/events") as response,
            ):
                lines = [line async for line in response.aiter_lines() if line]
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert lines == [
        "event: native-changed",
        'data: {"resources": ["jobs", "receipts"], "token": "100"}',
        "event: native-changed",
        'data: {"resources": ["requests"], "token": "101"}',
    ]


@pytest.mark.asyncio
async def test_events_missing_native_root_terminates_without_watcher(workspace: NativeWorkspace) -> None:
    app.dependency_overrides[get_workspace] = lambda: workspace
    called = False

    async def _unexpected(*_args: object, **_kwargs: object):
        nonlocal called
        called = True
        yield set()

    try:
        with patch("owlbear_cockpit.routes.events.awatch", _unexpected):
            transport = httpx.ASGITransport(app=app)
            async with (
                httpx.AsyncClient(transport=transport, base_url="http://test") as client,
                client.stream("GET", "/api/events") as response,
            ):
                body = [line async for line in response.aiter_lines()]
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert body == []
    assert called is False


def test_legacy_inventory_is_bounded_read_only_and_preserves_provenance(
    workspace: NativeWorkspace, tmp_path: Path
) -> None:
    source = tmp_path / "legacy-source"
    for relative in ("tasks/1.md", "decisions/pending/request-1.yaml", "activity.jsonl"):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"opaque legacy bytes for {relative}\n", encoding="utf-8")
    create_legacy_snapshot(source, workspace.legacy_snapshot_root, (), {})
    before = _store_state(source)
    app.dependency_overrides[get_workspace] = lambda: workspace
    try:
        with TestClient(app) as client:
            response = client.get("/api/legacy", params={"limit": 1})
            write = client.post("/api/legacy", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tasks"]) == 1
    assert payload["tasks"][0]["provenance"] == "tasks"
    assert payload["tasks"][0]["task"]["relative_path"] == "tasks/1.md"
    assert len(payload["requests"]) == 1
    assert payload["requests"][0]["provenance"] == "decisions/pending"
    assert payload["requests"][0]["request"]["relative_path"] == "decisions/pending/request-1.yaml"
    assert len(payload["activity"]) == 1
    assert payload["activity"][0]["provenance"] == "activity.jsonl"
    assert set(payload) == {"tasks", "requests", "activity", "truncated"}
    assert payload["activity"][0]["event"]["relative_path"] == "activity.jsonl"
    assert write.status_code == 405
    assert _store_state(source) == before


def test_empty_legacy_inventory_and_limit_validation(workspace: NativeWorkspace) -> None:
    app.dependency_overrides[get_workspace] = lambda: workspace
    try:
        with TestClient(app) as client:
            response = client.get("/api/legacy")
            invalid = client.get("/api/legacy", params={"limit": 101})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "tasks": [],
        "requests": [],
        "activity": [],
        "truncated": {"tasks": False, "requests": False, "activity": False},
    }
    assert invalid.status_code == 422


def test_assembled_app_removes_generic_surface_and_keeps_native_peer_services(
    workspace: NativeWorkspace,
) -> None:
    schema = app.openapi()
    paths = schema["paths"]
    forbidden = {
        "/api/board",
        "/api/tasks",
        "/api/tasks/{task_id}",
        "/api/tasks/{task_id}/activity",
        "/api/activity",
        "/api/sessions",
        "/api/requests/pending",
        "/api/requests/{request_id}/resolve",
        "/health",
        "/health/tasks",
        "/health/requests",
        "/health/tasks/repair",
    }
    required = {
        "/api/events",
        "/api/legacy",
        "/api/changes",
        "/api/memories",
        "/api/ideas",
        "/health/live",
        "/health/memory",
        "/health/ideas",
    }

    assert not forbidden.intersection(paths)
    assert required <= paths.keys()
    assert set(paths["/api/legacy"]) == {"get"}

    app.dependency_overrides[get_workspace] = lambda: workspace
    try:
        with TestClient(app) as client:
            assert client.get("/api/tasks").status_code == 404
            assert client.post("/api/tasks/1/release", json={}).status_code == 404
            assert client.get("/api/requests/pending").status_code == 404
            assert client.get("/health/live").json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
