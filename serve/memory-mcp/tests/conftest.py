"""Keep every memory-server test away from the machine's shared data repository."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp.server import AppContext


@pytest.fixture(autouse=True)
def _no_shared_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """No shared repository and no named folders, so no real store is read or written; tests set their own."""
    monkeypatch.setenv("OWLBEAR_DATA", "")  # empty means none, so the real pointer is never read
    monkeypatch.delenv("OWLBEAR_MEMORY_DIR", raising=False)
    monkeypatch.delenv("OWLBEAR_MEMORY_GLOBAL_DIR", raising=False)
    monkeypatch.delenv("OWLBEAR_MEMORY_AGENTS", raising=False)


@pytest.fixture
def memory_entry() -> Callable[..., MemoryEntry]:
    """Seed validated files as preconditions, without exercising unrelated lifecycle transitions."""

    def write(folder: Path, title: str, **fields: object) -> MemoryEntry:
        state = fields.get("state", MemoryState.PENDING)
        timestamp = "2026-01-01T00:00:00+00:00"
        entry = MemoryEntry.model_validate(
            {
                "id": str(uuid4()),
                "title": title,
                "content": f"{title} content.",
                "categories": ["process"],
                "confidence": 0.8,
                "score": 0.8,
                "state": state,
                "scope_agents": [] if state == MemoryState.PENDING else ["test-agent"],
                "source_agent": "test-agent",
                "created_at": timestamp,
                "updated_at": timestamp,
                "approved_at": timestamp if state == MemoryState.APPROVED else None,
            }
            | fields
        )
        storage.write_entry(folder / f"{entry.id}.md", entry, memory_dir=folder)
        return entry

    return write


@pytest.fixture
def memory_context() -> Callable[..., SimpleNamespace]:
    """Construct the ordinary server context, retaining an explicitly configured engine when needed."""

    def context(
        folder: Path,
        *,
        engine: MemoryEngine | None = None,
        global_dir: Path | None = None,
        agents: frozenset[str] = frozenset(),
    ) -> SimpleNamespace:
        return SimpleNamespace(
            request_context=SimpleNamespace(
                lifespan_context=AppContext(
                    engine=engine if engine is not None else MemoryEngine(folder),
                    memory_dir=folder,
                    global_dir=global_dir,
                    agents=agents,
                )
            )
        )

    return context
