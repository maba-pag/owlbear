"""Cockpit routing for failed duplicate repair."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from owlbear_memory import MemoryEngine, storage
from owlbear_memory.models import MemoryEntry

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@contextmanager
def _client_for_engine(engine: MemoryEngine) -> Iterator[TestClient]:
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_memory_engine  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_memory_engine] = lambda: engine
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_memory_engine, None)


def _snapshot(memory_dir: Path) -> tuple[tuple[str, bytes, int], ...]:
    return tuple((path.name, path.read_bytes(), path.stat().st_mtime_ns) for path in sorted(memory_dir.glob("*.md")))


def test_edit_duplicate_repair_failure_returns_mem_duplicate_id(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("real permission behavior cannot be verified as root")

    engine = MemoryEngine(tmp_path)
    newest = engine.save(
        title="Newest entry",
        content="newest content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    older = MemoryEntry.model_validate(
        newest.model_dump(mode="json")
        | {
            "title": "Older entry",
            "content": "older content",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    before = _snapshot(tmp_path)
    original_mode = tmp_path.stat().st_mode & 0o777

    try:
        tmp_path.chmod(original_mode & ~0o222)
        with _client_for_engine(engine) as client:
            response = client.post(
                f"/api/memories/{newest.id}/edit",
                json={"expected_updated_at": newest.updated_at, "content": "must not apply"},
            )
    finally:
        tmp_path.chmod(original_mode)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "MEM_DUPLICATE_ID"
    assert f"{newest.id}.md" in body["message"]
    assert "older-copy.md" in body["message"]
    assert _snapshot(tmp_path) == before
