"""Revision-bound challenges, replay and legacy challenge history."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage
from owlbear_memory.errors import ConcurrencyError, TransitionError, ValidationError
from owlbear_memory.models import ChallengeRecord

from owlbear_memory_mcp.server import AppContext
from owlbear_memory_mcp.tools import assess_memories, recall_memory

_TS = "2026-05-25T10:00:00+00:00"
_TS_APPROVED = "2026-05-20T08:00:00+00:00"
_ID = "550e8400-e29b-41d4-a716-446655451001"
_TASK_A, _TASK_B = "task-123", "task-456"


def _make_entry(state: MemoryState, **fields: object) -> MemoryEntry:
    return MemoryEntry(
        **{
            "id": _ID,
            "title": "Test Entry",
            "content": "Some content",
            "categories": ["domain-knowledge"],
            "confidence": 0.9,
            "state": state,
            "scope_agents": ["test-agent"],
            "source_agent": "test-agent",
            "created_at": _TS,
            "updated_at": _TS,
            "approved_at": None,
            **fields,
        }
    )


def _write_entry(directory: Path, entry: MemoryEntry) -> Path:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return path


def _write_legacy_entry(directory: Path, task_id: str | None) -> Path:
    path = directory / f"{_ID}.md"
    legacy_task = "null" if task_id is None else task_id
    path.write_text(
        "---\n"
        f"id: {_ID}\n"
        "title: Test Entry\n"
        "categories:\n"
        "- domain-knowledge\n"
        "confidence: 0.9\n"
        "state: contested\n"
        "scope_agents:\n"
        "- test-agent\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{_TS}'\n"
        "approved_at: null\n"
        f"contested_by_task: {legacy_task}\n"
        "---\n\nSome content\n",
        encoding="utf-8",
    )
    return path


def test_legacy_challenge_migrates_with_entry_revision_and_timestamp(tmp_path: Path) -> None:
    path = _write_legacy_entry(tmp_path, _TASK_A)
    engine = MemoryEngine(tmp_path)
    migrated = engine.get_entry(_ID)
    assert migrated.challenges == [ChallengeRecord(task_id=_TASK_A, revision=migrated.revision, recorded_at=_TS)]
    assert migrated.updated_at == _TS
    assert "contested_by_task" not in MemoryEntry.model_fields
    updated = engine.edit(_ID, {"title": "Updated"}, expected_revision=migrated.revision)
    reloaded = MemoryEngine(tmp_path).get_entry(_ID)
    assert updated.revision != migrated.revision
    assert reloaded.challenges == migrated.challenges
    assert "challenges:" in path.read_text(encoding="utf-8")
    assert "contested_by_task" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("legacy_task_id", ["task 1", "tâche-1", "t" * 200])
def test_legacy_challenge_keeps_previously_accepted_task_id(tmp_path: Path, legacy_task_id: str) -> None:
    path = _write_legacy_entry(tmp_path, legacy_task_id)
    engine = MemoryEngine(tmp_path)
    migrated = engine.get_entry(_ID)
    assert [challenge.task_id for challenge in migrated.challenges] == [legacy_task_id]
    engine.edit(_ID, {"title": "Updated"}, expected_revision=migrated.revision)
    assert [c.task_id for c in MemoryEngine(tmp_path).get_entry(_ID).challenges] == [legacy_task_id]
    assert "contested_by_task" not in path.read_text(encoding="utf-8")


def test_legacy_null_challenge_migrates_to_empty_list_and_is_removed_on_write(tmp_path: Path) -> None:
    path = _write_legacy_entry(tmp_path, None)
    engine = MemoryEngine(tmp_path)
    migrated = engine.get_entry(_ID)
    assert migrated.challenges == []
    updated = engine.edit(_ID, {"title": "Updated"}, expected_revision=migrated.revision)
    assert updated.challenges == []
    serialized = path.read_text(encoding="utf-8")
    assert "challenges:" in serialized
    assert "contested_by_task" not in serialized


@pytest.mark.asyncio
@pytest.mark.usefixtures("todays_memory_values")
@pytest.mark.parametrize("state", [MemoryState.APPROVED, MemoryState.CURATED])
async def test_challenges_replay_and_dispute_without_changing_ratings(tmp_path: Path, state: MemoryState) -> None:
    entry = _make_entry(
        state,
        approved_at=_TS_APPROVED if state == MemoryState.APPROVED else None,
        outstanding_count=3,
        unremarkable_count=1,
        didnt_use_count=2,
        score=0.95,
    )
    path = _write_entry(tmp_path, entry)
    engine = MemoryEngine(tmp_path)
    ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=AppContext(engine, tmp_path)))
    item = {"entry_id": entry.id, "revision": entry.revision, "bucket": "factually_wrong"}

    [first] = (await assess_memories(ctx, assessments=[item], task_id=_TASK_A))["results"]
    contested = MemoryEngine(tmp_path).get_entry(entry.id)
    assert (first["success"], first["already_applied"], first["recorded_bucket"]) == (True, False, "factually_wrong")
    assert contested.state == MemoryState.CONTESTED
    assert contested.approved_at is None
    assert contested.revision == entry.revision
    assert contested.updated_at != entry.updated_at
    assert contested.challenges == [
        ChallengeRecord(task_id=_TASK_A, revision=entry.revision, recorded_at=contested.updated_at)
    ]
    assert await recall_memory(ctx, agent="test-agent") == (
        f"## Test Entry\nEntry ID: `{entry.id}`\nRevision: `{entry.revision}`\n"
        f"State: contested\nChallenge task: `{_TASK_A}`\nSome content"
    )
    before = path.read_bytes()
    [replay] = (await assess_memories(ctx, assessments=[item], task_id=_TASK_A))["results"]
    assert replay == {**first, "already_applied": True}
    assert path.read_bytes() == before

    [second] = (await assess_memories(ctx, assessments=[item], task_id=_TASK_B))["results"]
    disputed = MemoryEngine(tmp_path).get_entry(entry.id)
    assert (second["success"], second["already_applied"], second["recorded_bucket"]) == (True, False, "factually_wrong")
    assert disputed.state == MemoryState.DISPUTED
    assert disputed.approved_at is None
    assert disputed.revision == entry.revision
    assert disputed.challenges == [
        *contested.challenges,
        ChallengeRecord(task_id=_TASK_B, revision=entry.revision, recorded_at=disputed.updated_at),
    ]
    assert entry.id not in await recall_memory(ctx, agent="test-agent")
    # Reload before replay: persisted receipts must win before the disputed-state guard.
    ctx.request_context.lifespan_context.engine = MemoryEngine(tmp_path)
    before = path.read_bytes()
    [replay] = (await assess_memories(ctx, assessments=[item], task_id=_TASK_B))["results"]
    assert replay == {**second, "already_applied": True}
    assert path.read_bytes() == before
    for checkpoint in (contested, disputed, MemoryEngine(tmp_path).get_entry(entry.id)):
        assert (
            checkpoint.outstanding_count,
            checkpoint.unremarkable_count,
            checkpoint.didnt_use_count,
            checkpoint.score,
        ) == (3, 1, 2, 0.95)


def test_contested_with_no_challenges_stays_contested_and_records_first(tmp_path: Path) -> None:
    entry = _make_entry(MemoryState.CONTESTED)
    _write_entry(tmp_path, entry)
    result = MemoryEngine(tmp_path).record_factually_wrong(_ID, _TASK_B, expected_revision=entry.revision).entry
    assert result.state == MemoryState.CONTESTED
    assert [c.task_id for c in result.challenges] == [_TASK_B]
    assert result.challenges[0].revision == entry.revision


def test_challenge_without_receipt_is_deduplicated_before_state_guard(tmp_path: Path) -> None:
    entry = _make_entry(MemoryState.CONTESTED)
    entry.challenges = [ChallengeRecord(task_id=_TASK_A, revision=entry.revision, recorded_at=_TS)]
    path = _write_entry(tmp_path, entry)
    before = path.read_bytes()
    replay = MemoryEngine(tmp_path).record_factually_wrong(_ID, _TASK_A, expected_revision=entry.revision)
    assert replay.already_applied is True
    assert replay.recorded_bucket == "factually_wrong"
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("state", "task_id", "stale", "error"),
    [
        (MemoryState.APPROVED, "", False, ValidationError),
        (MemoryState.APPROVED, "   ", False, ValidationError),
        (MemoryState.APPROVED, _TASK_A, True, ConcurrencyError),
        (MemoryState.PENDING, _TASK_A, True, ConcurrencyError),
        (MemoryState.APPROVED, "", True, ConcurrencyError),
        (MemoryState.APPROVED, "   ", True, ConcurrencyError),
    ],
)
def test_challenge_input_and_guard_order(
    tmp_path: Path, state: MemoryState, task_id: str, *, stale: bool, error: type[Exception]
) -> None:
    entry = _make_entry(state)
    path = _write_entry(tmp_path, entry)
    engine = MemoryEngine(tmp_path)
    revision = entry.revision
    if stale:
        engine.edit(_ID, {"content": "Actually changed after recall"}, expected_revision=revision)
    before = path.read_bytes()
    with pytest.raises(error):
        engine.record_factually_wrong(_ID, task_id, expected_revision=revision)
    assert path.read_bytes() == before


@pytest.mark.parametrize("state", [MemoryState.PENDING, MemoryState.DISPUTED, MemoryState.STALE, MemoryState.DELETED])
def test_challenge_state_guards(tmp_path: Path, state: MemoryState) -> None:
    entry = _make_entry(state)
    path = _write_entry(tmp_path, entry)
    before = path.read_bytes()
    with pytest.raises(TransitionError):
        MemoryEngine(tmp_path).record_factually_wrong(_ID, _TASK_A, expected_revision=entry.revision)
    assert path.read_bytes() == before
