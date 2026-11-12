"""Batch validation, rating writes and native per-item assessment failures."""

from __future__ import annotations

from itertools import count
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage
from owlbear_memory.errors import ConcurrencyError, TransitionError

from owlbear_memory_mcp.server import AppContext, mcp
from owlbear_memory_mcp.tools import assess_memories

pytestmark = pytest.mark.usefixtures("todays_memory_values")
_TS = "2026-05-25T10:00:00+00:00"
_ID_APPROVED = "550e8400-e29b-41d4-a716-446655441860"
_ID_CURATED = "550e8400-e29b-41d4-a716-446655441861"
_ID_CONTESTED = "550e8400-e29b-41d4-a716-446655441862"
_ID_PENDING = "550e8400-e29b-41d4-a716-446655441863"
_ID_MISSING = "550e8400-e29b-41d4-a716-446655441866"
_ID_CURATED_B = "550e8400-e29b-41d4-a716-446655441867"
_TASK_IDS = count()


def _make_entry(entry_id: str, state: str, **fields: object) -> MemoryEntry:
    return MemoryEntry(
        **{
            "id": entry_id,
            "title": f"Entry-{state}",
            "content": f"Content for {state} entry.",
            "categories": ["domain-knowledge"],
            "confidence": 0.8,
            "state": state,
            "scope_agents": ["test-agent"],
            "source_agent": "test-agent",
            "created_at": _TS,
            "updated_at": _TS,
            "approved_at": _TS if state == "approved" else None,
            "score": 0.8,
            **fields,
        }
    )


def _seed_entry(directory: Path, entry: MemoryEntry) -> Path:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return path


def _make_ctx(engine: MemoryEngine, directory: Path) -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context=AppContext(engine=engine, memory_dir=directory))
    )


def _record_assessment(engine: MemoryEngine, entry_id: str, bucket: str) -> MemoryEntry:
    entry = engine.get_entry(entry_id)
    return engine.record_assessment(
        entry_id,
        bucket,
        task_id=f"assessment-test-{next(_TASK_IDS)}",
        expected_revision=entry.revision,
        stale_factor=50,
    ).entry


@pytest.mark.asyncio
async def test_assess_memories_registered_on_mcp_server() -> None:
    assert "assess_memories" in [tool.name for tool in await mcp.list_tools()]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("invalid", "task_id"),
    [
        ("empty-batch", "task-1"),
        ("valid", ""),
        ("valid", "   "),
        ("invalid-bucket", "task-1"),
        ("invalid-after-valid", "task-1"),
        ("non-dict", "task-1"),
        ("missing-bucket", "task-1"),
        ("missing-entry-id", "task-1"),
    ],
)
async def test_invalid_assessment_batch_is_rejected_before_mutation(tmp_path: Path, invalid: str, task_id: str) -> None:
    entry = _make_entry(_ID_APPROVED, "approved", outstanding_count=3)
    path = _seed_entry(tmp_path, entry)
    engine = MemoryEngine(tmp_path)
    valid = {"entry_id": entry.id, "revision": entry.revision, "bucket": "outstanding"}
    batches = {
        "empty-batch": [],
        "valid": [valid],
        "invalid-bucket": [{**valid, "bucket": "invalid"}],
        "invalid-after-valid": [valid, {**valid, "bucket": "INVALID"}],
        "non-dict": ["not_a_dict"],
        "missing-bucket": [{"entry_id": entry.id, "revision": entry.revision}],
        "missing-entry-id": [{"revision": entry.revision, "bucket": "outstanding"}],
    }
    before = path.read_bytes()
    with pytest.raises(ToolError) as raised:
        await assess_memories(_make_ctx(engine, tmp_path), assessments=batches[invalid], task_id=task_id)
    assert all(
        bucket in str(raised.value) for bucket in ("outstanding", "unremarkable", "didnt_use", "factually_wrong")
    )
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("state", "bucket"),
    [
        ("approved", "outstanding"),
        ("approved", "unremarkable"),
        ("approved", "didnt_use"),
        ("curated", "unremarkable"),
        ("contested", "didnt_use"),
    ],
)
def test_rating_write_contract(tmp_path: Path, state: str, bucket: str) -> None:
    entry = _make_entry(_ID_APPROVED, state, outstanding_count=2, unremarkable_count=5, didnt_use_count=10, score=0.123)
    path = _seed_entry(tmp_path, entry)
    outcome = MemoryEngine(tmp_path).record_assessment(
        entry.id, bucket, task_id="rating-write", expected_revision=entry.revision, stale_factor=50
    )
    persisted = MemoryEngine(tmp_path).get_entry(entry.id)
    before, after = entry.model_dump(), persisted.model_dump()
    field = f"{bucket}_count"
    assert {key for key in before if before[key] != after[key]} == {field, "updated_at", "assessment_receipts"}
    assert before.keys() == after.keys()
    assert after[field] == before[field] + 1
    assert persisted.revision == entry.revision
    assert persisted.score == 0.123
    assert outcome.entry == persisted == storage.read_entry(path)
    assert (outcome.already_applied, outcome.recorded_bucket) == (False, bucket)
    assert [r.model_dump() for r in persisted.assessment_receipts] == [
        {"task_id": "rating-write", "revision": entry.revision, "bucket": bucket}
    ]


@pytest.mark.parametrize("state", ["pending", "deleted", "stale", "approved"])
def test_rating_state_and_revision_guards(tmp_path: Path, state: str) -> None:
    entry = _make_entry(_ID_APPROVED, state)
    path = _seed_entry(tmp_path, entry)
    engine = MemoryEngine(tmp_path)
    if state == "approved":
        engine.edit(entry.id, {"content": "Changed after recall"}, expected_revision=entry.revision)
    before = path.read_bytes()
    with pytest.raises(ConcurrencyError if state == "approved" else TransitionError):
        engine.record_assessment(
            entry.id, "outstanding", task_id="assessment-conflict", expected_revision=entry.revision, stale_factor=50
        )
    assert path.read_bytes() == before


@pytest.mark.parametrize(("factor", "expected"), [(51, MemoryState.APPROVED), (50, MemoryState.STALE)])
def test_the_stale_factor_decides_at_the_boundary(tmp_path: Path, factor: int, expected: MemoryState) -> None:
    entry = _make_entry(_ID_APPROVED, "approved", didnt_use_count=50)
    _seed_entry(tmp_path, entry)
    outcome = MemoryEngine(tmp_path).record_assessment(
        entry.id, "didnt_use", task_id="stale-boundary", expected_revision=entry.revision, stale_factor=factor
    )
    assert outcome.entry.state == expected


def test_slot_efficiency_not_exceeded_state_unchanged(tmp_path: Path) -> None:
    entry = _make_entry(_ID_APPROVED, "approved", outstanding_count=10, didnt_use_count=1)
    _seed_entry(tmp_path, entry)
    assert _record_assessment(MemoryEngine(tmp_path), entry.id, "didnt_use").state == MemoryState.APPROVED


@pytest.mark.asyncio
async def test_batch_failures_continue_and_successes_persist(tmp_path: Path) -> None:
    approved = _make_entry(_ID_APPROVED, "approved", outstanding_count=3)
    curated = _make_entry(_ID_CURATED, "curated", unremarkable_count=2)
    pending = _make_entry(_ID_PENDING, "pending")
    stale_rating = _make_entry(_ID_CURATED_B, "approved")
    stale_challenge = _make_entry(_ID_CONTESTED, "approved")
    for entry in (approved, curated, pending, stale_rating, stale_challenge):
        _seed_entry(tmp_path, entry)
    engine = MemoryEngine(tmp_path)
    for entry in (stale_rating, stale_challenge):
        engine.edit(entry.id, {"content": "Changed after recall"}, expected_revision=entry.revision)
    failed_bytes = {
        entry.id: (tmp_path / f"{entry.id}.md").read_bytes() for entry in (pending, stale_rating, stale_challenge)
    }
    assessments = [
        {"entry_id": _ID_MISSING, "revision": "0" * 16, "bucket": "outstanding"},
        {"entry_id": pending.id, "revision": pending.revision, "bucket": "factually_wrong"},
        {"entry_id": pending.id, "revision": pending.revision, "bucket": "outstanding"},
        {"entry_id": stale_rating.id, "revision": stale_rating.revision, "bucket": "outstanding"},
        {"entry_id": stale_challenge.id, "revision": stale_challenge.revision, "bucket": "factually_wrong"},
        {"entry_id": approved.id, "revision": approved.revision, "bucket": "outstanding"},
        {"entry_id": curated.id, "revision": curated.revision, "bucket": "unremarkable"},
    ]
    ctx = _make_ctx(engine, tmp_path)
    result = await assess_memories(ctx, assessments=assessments, task_id="mixed-batch")
    assert set(result) == {"results"}
    rows = result["results"]
    assert len(rows) == len(assessments)
    assert [row["entry_id"] for row in rows] == [item["entry_id"] for item in assessments]
    assert [row["success"] for row in rows] == [False] * 5 + [True, True]
    for row, diagnostic in zip(
        rows[:5],
        ["Entry not found", "state pending", "state pending", "changed since recall", "changed since recall"],
        strict=True,
    ):
        assert set(row) == {"entry_id", "success", "error"}
        assert diagnostic in row["error"]
    for row, entry, bucket in zip(rows[5:], (approved, curated), ("outstanding", "unremarkable"), strict=True):
        assert row == {"entry_id": entry.id, "success": True, "already_applied": False, "recorded_bucket": bucket}
    assert MemoryEngine(tmp_path).get_entry(approved.id).outstanding_count == 4
    assert MemoryEngine(tmp_path).get_entry(curated.id).unremarkable_count == 3
    for entry_id, before in failed_bytes.items():
        assert (tmp_path / f"{entry_id}.md").read_bytes() == before

    paths = [tmp_path / f"{entry.id}.md" for entry in (approved, curated, pending, stale_rating, stale_challenge)]
    before = {path.name: path.read_bytes() for path in paths}
    ctx = _make_ctx(MemoryEngine(tmp_path), tmp_path)
    replay = await assess_memories(ctx, assessments=assessments, task_id="mixed-batch")
    assert replay["results"] == rows[:5] + [{**row, "already_applied": True} for row in rows[5:]]
    assert {path.name: path.read_bytes() for path in paths} == before
