"""Scope filtering, exact identity-bearing recall and revision refresh."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp.server import AppContext
from owlbear_memory_mcp.tools import recall_memory

pytestmark = pytest.mark.usefixtures("todays_memory_values")
_TS = "2026-05-04T10:00:00Z"


def _uuid(n: int) -> str:
    return f"550e8400-e29b-41d4-a716-4466554{n:05d}"


def _make_entry(**overrides: object) -> MemoryEntry:
    return MemoryEntry(
        **{
            "id": _uuid(1),
            "title": "Test entry",
            "categories": ["domain-knowledge"],
            "confidence": 0.85,
            "state": "curated",
            "content": "Entry body text.",
            "scope_agents": ["builder"],
            "source_agent": "builder",
            "created_at": _TS,
            "updated_at": _TS,
            "approved_at": None,
            **overrides,
        }
    )


def _make_ctx(engine: MemoryEngine, directory: Path) -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context=AppContext(engine=engine, memory_dir=directory))
    )


def _seed_entry(directory: Path, entry: MemoryEntry) -> MemoryEntry:
    storage.write_entry(directory / f"{entry.id}.md", entry, memory_dir=directory)
    return entry


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "scope", "caller", "visible"),
    [
        ("curated", ["builder"], "builder", True),
        ("curated", ["reviewer"], "builder", False),
        ("curated", ["builder", "reviewer"], "builder", True),
        ("curated", ["*"], "builder", True),
        ("curated", ["*"], "doc-writer", True),
        ("approved", ["*"], "architect", True),
        ("curated", [], "builder", False),
        ("approved", [], "builder", False),
    ],
)
async def test_recall_scope_matrix(tmp_path: Path, state: str, scope: list[str], caller: str, *, visible: bool) -> None:
    entry = _seed_entry(tmp_path, _make_entry(state=state, scope_agents=scope))
    ctx = _make_ctx(MemoryEngine(tmp_path), tmp_path)
    result = await recall_memory(ctx, agent=caller)
    assert (f"Entry ID: `{entry.id}`" in result) is visible


@pytest.mark.asyncio
async def test_mix_unscoped_and_scoped_only_scoped_returned(tmp_path: Path) -> None:
    _seed_entry(tmp_path, _make_entry(id=_uuid(1), title="Unscoped entry", scope_agents=[]))
    scoped = _seed_entry(tmp_path, _make_entry(id=_uuid(2), title="Scoped entry"))
    result = await recall_memory(_make_ctx(MemoryEngine(tmp_path), tmp_path), agent="builder")
    assert result == f"## Scoped entry\nEntry ID: `{scoped.id}`\nRevision: `{scoped.revision}`\nEntry body text."


@pytest.mark.asyncio
async def test_wildcard_agent_receives_guidance(tmp_path: Path) -> None:
    result = await recall_memory(_make_ctx(MemoryEngine(tmp_path), tmp_path), agent="*")
    assert result == (
        "This recall_memory caller is not recognized from stored memory data. Known agents: none discovered. "
        "It receives only memories scoped to all agents (*); recognition is relevance scoping, "
        "not write authorization."
    )


@pytest.mark.asyncio
async def test_revision_refreshes_after_edit_from_second_engine(tmp_path: Path) -> None:
    entry = _seed_entry(tmp_path, _make_entry(id=_uuid(99), title="Cross-engine revision", content="Original body."))
    ctx = _make_ctx(MemoryEngine(tmp_path), tmp_path)
    initial = await recall_memory(ctx, agent="builder")
    assert f"Entry ID: `{entry.id}`\nRevision: `{entry.revision}`" in initial
    edited = MemoryEngine(tmp_path).edit(entry.id, {"content": "Updated body."}, expected_updated_at=entry.updated_at)
    assert edited.revision != entry.revision
    result = await recall_memory(ctx, agent="builder")
    assert f"Entry ID: `{entry.id}`\nRevision: `{edited.revision}`" in result
    assert f"Revision: `{entry.revision}`" not in result
    assert "Updated body." in result


@pytest.mark.asyncio
async def test_two_entries_keep_ids_paired_and_use_double_newline_separator(tmp_path: Path) -> None:
    e1 = _seed_entry(
        tmp_path,
        _make_entry(
            id=_uuid(1),
            title="Alpha Entry",
            content="Alpha content.",
            confidence=0.92,
            scope_agents=["recall-scope-tester"],
            source_agent="builder",
            created_at="2026-01-15T08:30:00Z",
            updated_at="2026-02-20T14:15:00Z",
        ),
    )
    e2 = _seed_entry(
        tmp_path,
        _make_entry(id=_uuid(2), title="Beta Entry", content="Beta content.", scope_agents=["recall-scope-tester"]),
    )
    result = await recall_memory(_make_ctx(MemoryEngine(tmp_path), tmp_path), agent="recall-scope-tester")
    assert result == (
        f"## Alpha Entry\nEntry ID: `{e1.id}`\nRevision: `{e1.revision}`\nAlpha content.\n\n"
        f"## Beta Entry\nEntry ID: `{e2.id}`\nRevision: `{e2.revision}`\nBeta content."
    )


@pytest.mark.asyncio
async def test_contested_entry_without_task_still_includes_state_marker(tmp_path: Path) -> None:
    entry = _seed_entry(tmp_path, _make_entry(title="Unreferenced challenge", state=MemoryState.CONTESTED))
    result = await recall_memory(_make_ctx(MemoryEngine(tmp_path), tmp_path), agent="builder")
    assert result == (
        f"## Unreferenced challenge\nEntry ID: `{entry.id}`\nRevision: `{entry.revision}`\n"
        "State: contested\nEntry body text."
    )
    assert "Challenge task:" not in result


@pytest.mark.asyncio
async def test_mixed_recall_marks_only_contested_entries(tmp_path: Path) -> None:
    approved = _seed_entry(
        tmp_path,
        _make_entry(
            id=_uuid(1), title="Approved guidance", content="Approved body.", state="approved", confidence=0.95
        ),
    )
    contested = _seed_entry(
        tmp_path,
        _make_entry(
            id=_uuid(2), title="Contested guidance", content="Contested body.", state="approved", confidence=0.85
        ),
    )
    curated = _seed_entry(
        tmp_path, _make_entry(id=_uuid(3), title="Curated guidance", content="Curated body.", confidence=0.8)
    )
    engine = MemoryEngine(tmp_path)
    contested = engine.record_factually_wrong(
        contested.id, "task-mixed-243", expected_revision=contested.revision
    ).entry
    result = await recall_memory(_make_ctx(engine, tmp_path), agent="builder")
    assert result == "\n\n".join(
        (
            f"## Approved guidance\nEntry ID: `{approved.id}`\nRevision: `{approved.revision}`\nApproved body.",
            (
                f"## Contested guidance\nEntry ID: `{contested.id}`\nRevision: `{contested.revision}`\n"
                "State: contested\nChallenge task: `task-mixed-243`\nContested body."
            ),
            f"## Curated guidance\nEntry ID: `{curated.id}`\nRevision: `{curated.revision}`\nCurated body.",
        )
    )


@pytest.mark.asyncio
async def test_limit_caps_number_of_entries_returned(tmp_path: Path) -> None:
    for i in range(1, 6):
        _seed_entry(tmp_path, _make_entry(id=_uuid(i), title=f"Entry {i}"))
    result = await recall_memory(_make_ctx(MemoryEngine(tmp_path), tmp_path), agent="builder", limit=2)
    assert sum(line.startswith("## ") for line in result.splitlines()) == 2
