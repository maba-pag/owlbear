"""List priority and exceptional-state resolution, editing and tombstones."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage
from owlbear_memory.errors import ConcurrencyError, TransitionError
from owlbear_memory.models import ChallengeRecord

from owlbear_memory_mcp.server import AppContext
from owlbear_memory_mcp.tools import _state_rank_for_list, list_memories

_TS = "2026-05-25T10:00:00+00:00"
_ID = "550e8400-e29b-41d4-a716-446655441001"
_EXCEPTIONAL = [MemoryState.CONTESTED, MemoryState.DISPUTED, MemoryState.STALE]


def _make_existing_entry(state: MemoryState, **fields: object) -> MemoryEntry:
    return MemoryEntry(
        **{
            "id": _ID,
            "title": f"Entry-{state}",
            "content": f"Content for {state} entry.",
            "categories": ["domain-knowledge"],
            "confidence": 0.9,
            "state": state,
            "scope_agents": ["test-agent"],
            "source_agent": "test-agent",
            "created_at": _TS,
            "updated_at": _TS,
            "approved_at": _TS,
            "didnt_use_count": 5,
            "challenges": [
                ChallengeRecord(task_id="task-1", revision="0123456789abcdef", recorded_at=_TS),
                ChallengeRecord(task_id="task-2", revision="0123456789abcdef", recorded_at=_TS),
            ],
            **fields,
        }
    )


def _write_existing_entry(directory: Path, entry: MemoryEntry) -> Path:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return path


@pytest.mark.parametrize(
    ("state", "rank"),
    [
        (MemoryState.PENDING, 0),
        (MemoryState.CURATED, 1),
        (MemoryState.CONTESTED, 1),
        (MemoryState.APPROVED, 2),
        (MemoryState.DISPUTED, 3),
        (MemoryState.STALE, 3),
        (MemoryState.DELETED, 3),
    ],
)
def test_list_state_rank_contract(state: MemoryState, rank: int) -> None:
    assert _state_rank_for_list(state) == rank


@pytest.mark.asyncio
async def test_list_priority_and_default_states(tmp_path: Path) -> None:
    # Reverse IDs keep ordering by ID alone from passing the rank contract.
    states = [
        MemoryState.PENDING,
        MemoryState.CURATED,
        MemoryState.CONTESTED,
        MemoryState.APPROVED,
        MemoryState.DISPUTED,
        MemoryState.STALE,
        MemoryState.DELETED,
    ]
    entries = [
        _make_existing_entry(state, id=f"550e8400-e29b-41d4-a716-446655441{9 - index:03d}")
        for index, state in enumerate(states)
    ]
    for entry in entries:
        _write_existing_entry(tmp_path, entry)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context=AppContext(MemoryEngine(tmp_path), tmp_path))
    )
    result = await list_memories(ctx)
    assert [row["id"] for row in result] == [entries[index].id for index in (0, 2, 1, 3, 5, 4)]


@pytest.mark.parametrize("state", _EXCEPTIONAL)
def test_exception_resolution(tmp_path: Path, state: MemoryState) -> None:
    entry = _make_existing_entry(state, approved_at=None)
    _write_existing_entry(tmp_path, entry)
    result = MemoryEngine(tmp_path).resolve(entry.id, expected_updated_at=_TS)
    assert result.state == MemoryState.APPROVED
    assert result.approved_at == result.updated_at != _TS
    assert result.challenges == []
    assert result.didnt_use_count == (0 if state == MemoryState.STALE else 5)
    assert MemoryEngine(tmp_path).get_entry(entry.id) == result


@pytest.mark.parametrize(
    ("state", "timestamp", "error"),
    [
        (MemoryState.CONTESTED, "2025-01-01T00:00:00+00:00", ConcurrencyError),
        (MemoryState.PENDING, _TS, TransitionError),
        (MemoryState.APPROVED, _TS, TransitionError),
        (MemoryState.CURATED, _TS, TransitionError),
        (MemoryState.DELETED, _TS, TransitionError),
    ],
)
def test_exception_resolution_rejections(
    tmp_path: Path, state: MemoryState, timestamp: str, error: type[Exception]
) -> None:
    entry = _make_existing_entry(state)
    path = _write_existing_entry(tmp_path, entry)
    before = path.read_bytes()
    with pytest.raises(error):
        MemoryEngine(tmp_path).resolve(entry.id, expected_updated_at=timestamp)
    assert path.read_bytes() == before


@pytest.mark.parametrize("state", _EXCEPTIONAL)
def test_exception_edits_preserve_state_and_challenge_revision(tmp_path: Path, state: MemoryState) -> None:
    entry = _make_existing_entry(state)
    entry.challenges = [ChallengeRecord(task_id="task-1", revision=entry.revision, recorded_at=_TS)]
    _write_existing_entry(tmp_path, entry)
    result = MemoryEngine(tmp_path).edit(entry.id, {"title": "Updated"}, expected_updated_at=_TS)
    assert (result.title, result.state) == ("Updated", state)
    assert result.revision != entry.revision
    assert result.challenges == entry.challenges
    assert MemoryEngine(tmp_path).get_entry(entry.id) == result


@pytest.mark.parametrize("state", _EXCEPTIONAL)
def test_exceptional_delete_retains_tombstone_and_challenges(tmp_path: Path, state: MemoryState) -> None:
    entry = _make_existing_entry(state)
    path = _write_existing_entry(tmp_path, entry)
    result = MemoryEngine(tmp_path).delete(entry.id, expected_updated_at=_TS)
    assert result.state == MemoryState.DELETED
    assert result.challenges == entry.challenges
    tombstone = storage.read_entry(path)
    assert tombstone == result
    assert MemoryEngine(tmp_path).get_entry(entry.id) == result
