"""MCP assessment tool regression tests.

Behavioral coverage:
- AC1: assess_memories MCP tool validates assessments list (non-empty; ToolError if empty),
       task_id (non-empty; ToolError if empty/whitespace-only). Valid bucket values:
       outstanding, unremarkable, didnt_use, factually_wrong. Invalid bucket in any item
       raises ToolError with allowed values listed (aborts entire batch).
- AC2: Counter-increment path (outstanding/unremarkable/didnt_use): validates entry exists
       and is in voteable state (approved, curated, contested); increments corresponding
       counter; recomputes score via compute_score; calls check_slot_efficiency and if
       exceeded calls try_stale_transition.
- AC3: Factually-wrong path: validates entry exists and is in voteable state; delegates to
       record_factually_wrong(entry_id, task_id, expected_updated_at=entry.updated_at).
       No counter increment, no score recompute, no slot-efficiency check.
- AC4: Returns list of per-entry results with entry_id and success/error. Non-existent
       entry_id, non-voteable state, or ConcurrencyError produces a failure result for that
       entry (with error message) without aborting remaining assessments. Successful entries
       are persisted to disk atomically per entry.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState
from owlbear_memory import storage
from owlbear_memory.errors import ConcurrencyError, TransitionError

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"
_TS_WRONG = "2025-01-01T00:00:00+00:00"

_ID_APPROVED = "550e8400-e29b-41d4-a716-446655441860"
_ID_CURATED = "550e8400-e29b-41d4-a716-446655441861"
_ID_CONTESTED = "550e8400-e29b-41d4-a716-446655441862"
_ID_PENDING = "550e8400-e29b-41d4-a716-446655441863"
_ID_DELETED = "550e8400-e29b-41d4-a716-446655441864"
_ID_STALE = "550e8400-e29b-41d4-a716-446655441865"
_ID_MISSING = "550e8400-e29b-41d4-a716-446655441866"
_ID_CURATED_B = "550e8400-e29b-41d4-a716-446655441867"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(  # noqa: PLR0913
    entry_id: str,
    state: str,
    confidence: float = 0.8,
    outstanding_count: int = 0,
    unremarkable_count: int = 0,
    didnt_use_count: int = 0,
    score: float | None = None,
    updated_at: str = _TS,
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        title=f"Entry-{state}",
        content=f"Content for {state} entry.",
        categories=["domain-knowledge"],
        confidence=confidence,
        state=state,
        scope_agents=["test-agent"],
        source_agent="test-agent",
        created_at=_TS,
        updated_at=updated_at,
        approved_at=_TS if state == "approved" else None,
        outstanding_count=outstanding_count,
        unremarkable_count=unremarkable_count,
        didnt_use_count=didnt_use_count,
        score=score if score is not None else confidence,
    )


def _seed_entry(directory: Path, entry: MemoryEntry) -> None:
    """Write entry directly to disk; caller must call engine.load() after."""
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


# ---------------------------------------------------------------------------
# AC1 — Tool registration and input validation
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """AC1: assess_memories is importable and validates assessments/task_id/bucket."""

    def test_assess_memories_importable_from_tools(self) -> None:
        """assess_memories can be imported from owlbear_memory_mcp.tools."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        assert callable(assess_memories)

    @pytest.mark.asyncio
    async def test_assess_memories_registered_on_mcp_server(self) -> None:
        """assess_memories must appear in the MCP server tool registry.

        Directly importing from tools.py is insufficient — removing the @mcp.tool
        decorator in server.py would leave tool-import tests green. This test
        introspects owlbear_memory_mcp.server.mcp to confirm the server-side
        registration is present.
        """
        from owlbear_memory_mcp.server import mcp  # noqa: PLC0415

        registered_names = [tool.name for tool in await mcp.list_tools()]
        assert "assess_memories" in registered_names, (
            f"assess_memories not found in MCP server tool registry; registered: {registered_names}"
        )

    @pytest.mark.asyncio
    async def test_empty_assessments_list_raises_tool_error(self, tmp_path: Path) -> None:
        """Empty assessments list raises ToolError immediately (before any engine call)."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(ctx, assessments=[], task_id="task-1")

    @pytest.mark.asyncio
    async def test_empty_task_id_raises_tool_error(self, tmp_path: Path) -> None:
        """Empty string task_id raises ToolError."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": "outstanding"}],
                task_id="",
            )

    @pytest.mark.asyncio
    async def test_whitespace_only_task_id_raises_tool_error(self, tmp_path: Path) -> None:
        """Whitespace-only task_id raises ToolError."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": "outstanding"}],
                task_id="   ",
            )

    @pytest.mark.asyncio
    async def test_invalid_bucket_raises_tool_error(self, tmp_path: Path) -> None:
        """Invalid bucket value raises ToolError, not a per-item failure."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": "bogus_bucket"}],
                task_id="task-1",
            )

    @pytest.mark.asyncio
    async def test_invalid_bucket_error_includes_allowed_values(self, tmp_path: Path) -> None:
        """ToolError from invalid bucket includes allowed values in the message."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError) as exc_info:
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": "invalid"}],
                task_id="task-1",
            )

        error_msg = str(exc_info.value)
        # At least one valid bucket name must appear in the error message
        assert any(v in error_msg for v in ("outstanding", "unremarkable", "didnt_use", "factually_wrong"))

    @pytest.mark.asyncio
    async def test_invalid_bucket_aborts_entire_batch_not_per_item(self, tmp_path: Path) -> None:
        """Invalid bucket aborts the entire batch; valid items before it are not processed."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", outstanding_count=0)
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        # First item is valid, second has an invalid bucket
        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=[
                    {"entry_id": _ID_APPROVED, "bucket": "outstanding"},
                    {"entry_id": _ID_APPROVED, "bucket": "INVALID"},
                ],
                task_id="task-1",
            )

        # The batch was aborted — approved entry counter must be unchanged
        fresh_engine = MemoryEngine(memory_dir=tmp_path)
        persisted = fresh_engine.get_entry(_ID_APPROVED)
        assert persisted.outstanding_count == 0

    @pytest.mark.asyncio
    async def test_non_dict_item_in_assessments_raises_tool_error(self, tmp_path: Path) -> None:
        """Non-dict item in assessments list raises ToolError (batch aborts, not per-entry failure)."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=["not_a_dict"],  # type: ignore[list-item]
                task_id="task-1",
            )

    @pytest.mark.asyncio
    async def test_item_missing_bucket_key_raises_tool_error(self, tmp_path: Path) -> None:
        """Dict item missing 'bucket' key raises ToolError (batch aborts, not per-entry failure)."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED}],  # missing 'bucket'
                task_id="task-1",
            )

    @pytest.mark.asyncio
    async def test_item_missing_entry_id_key_raises_tool_error(self, tmp_path: Path) -> None:
        """Dict item missing 'entry_id' key raises ToolError (batch aborts, not per-entry failure)."""
        from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await assess_memories(
                ctx,
                assessments=[{"bucket": "outstanding"}],  # missing 'entry_id'
                task_id="task-1",
            )

    @pytest.mark.asyncio
    async def test_all_four_valid_bucket_values_accepted(self, tmp_path: Path) -> None:
        """All four valid bucket values complete without ToolError on a valid approved entry."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        for bucket in ("outstanding", "unremarkable", "didnt_use", "factually_wrong"):
            # Fresh approved entry for each bucket
            entry = _make_entry(_ID_APPROVED, "approved")
            _seed_entry(tmp_path, entry)
            engine.load()

            result = await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": bucket}],
                task_id="task-1",
            )
            assert isinstance(result, dict), f"Expected dict result for bucket={bucket}"


# ---------------------------------------------------------------------------
# AC2 — Counter-increment path: engine.record_assessment()
# ---------------------------------------------------------------------------


class TestCounterIncrementPath:
    """AC2: record_assessment engine method — counter increment, score recompute, stale trigger."""

    def test_record_assessment_method_exists_on_memory_engine(self, tmp_path: Path) -> None:
        """MemoryEngine exposes a record_assessment() method."""
        engine = MemoryEngine(memory_dir=tmp_path)
        assert hasattr(engine, "record_assessment"), "MemoryEngine.record_assessment method missing"
        assert callable(engine.record_assessment)

    def test_outstanding_bucket_increments_outstanding_count(self, tmp_path: Path) -> None:
        """outstanding bucket increments outstanding_count by exactly 1."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", outstanding_count=2)
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "outstanding")
        assert updated.outstanding_count == 3

    def test_unremarkable_bucket_increments_unremarkable_count(self, tmp_path: Path) -> None:
        """unremarkable bucket increments unremarkable_count by exactly 1."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", unremarkable_count=5)
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "unremarkable")
        assert updated.unremarkable_count == 6

    def test_didnt_use_bucket_increments_didnt_use_count(self, tmp_path: Path) -> None:
        """didnt_use bucket increments didnt_use_count by exactly 1."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", didnt_use_count=10)
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "didnt_use")
        assert updated.didnt_use_count == 11

    def test_outstanding_increment_only_changes_outstanding_count(self, tmp_path: Path) -> None:
        """outstanding bucket leaves unremarkable_count and didnt_use_count unchanged."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "outstanding")
        assert updated.unremarkable_count == 0
        assert updated.didnt_use_count == 0

    def test_score_recomputed_after_outstanding_increment(self, tmp_path: Path) -> None:
        """Score is recomputed via compute_score formula after outstanding increment."""
        from owlbear_memory.engine import OUTSTANDING_BOOST, compute_score  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        confidence = 0.8
        entry = _make_entry(_ID_APPROVED, "approved", confidence=confidence, outstanding_count=1)
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "outstanding")
        expected = compute_score(confidence, 2, 0)
        assert updated.score == pytest.approx(expected)
        assert updated.score == pytest.approx(confidence + 2 * OUTSTANDING_BOOST)

    def test_score_recomputed_after_unremarkable_increment(self, tmp_path: Path) -> None:
        """Score is recomputed via compute_score formula after unremarkable increment."""
        from owlbear_memory.engine import UNREMARKABLE_PENALTY, compute_score  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        confidence = 0.9
        entry = _make_entry(_ID_APPROVED, "approved", confidence=confidence, unremarkable_count=2)
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "unremarkable")
        expected = compute_score(confidence, 0, 3)
        assert updated.score == pytest.approx(expected)
        assert updated.score == pytest.approx(confidence - 3 * UNREMARKABLE_PENALTY)

    def test_approved_entry_is_voteable(self, tmp_path: Path) -> None:
        """approved state is a valid voteable state for counter-increment assessment."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "outstanding")
        assert updated.outstanding_count == 1

    def test_curated_entry_is_voteable(self, tmp_path: Path) -> None:
        """curated state is a valid voteable state for counter-increment assessment."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_CURATED, "curated")
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_CURATED, "unremarkable")
        assert updated.unremarkable_count == 1

    def test_contested_entry_is_voteable(self, tmp_path: Path) -> None:
        """contested state is a valid voteable state for counter-increment assessment."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_CONTESTED, "contested")
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_CONTESTED, "didnt_use")
        assert updated.didnt_use_count == 1

    def test_pending_entry_raises_transition_error(self, tmp_path: Path) -> None:
        """pending state is not voteable — record_assessment raises TransitionError."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_PENDING, "pending")
        _seed_entry(tmp_path, entry)
        engine.load()

        with pytest.raises(TransitionError):
            engine.record_assessment(_ID_PENDING, "outstanding")

    def test_deleted_entry_raises_transition_error(self, tmp_path: Path) -> None:
        """deleted state is not voteable — record_assessment raises TransitionError."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_DELETED, "deleted")
        _seed_entry(tmp_path, entry)
        engine.load()

        with pytest.raises(TransitionError):
            engine.record_assessment(_ID_DELETED, "outstanding")

    def test_stale_entry_raises_transition_error(self, tmp_path: Path) -> None:
        """stale state is not voteable — record_assessment raises TransitionError."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_STALE, "stale")
        _seed_entry(tmp_path, entry)
        engine.load()

        with pytest.raises(TransitionError):
            engine.record_assessment(_ID_STALE, "outstanding")

    def test_occ_mismatch_raises_concurrency_error(self, tmp_path: Path) -> None:
        """ConcurrencyError raised when expected_updated_at doesn't match entry updated_at."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", updated_at=_TS)
        _seed_entry(tmp_path, entry)
        engine.load()

        with pytest.raises(ConcurrencyError):
            engine.record_assessment(_ID_APPROVED, "outstanding", expected_updated_at=_TS_WRONG)

    def test_occ_match_succeeds(self, tmp_path: Path) -> None:
        """No error when expected_updated_at matches entry's current updated_at."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", updated_at=_TS)
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "outstanding", expected_updated_at=_TS)
        assert updated.outstanding_count == 1

    def test_slot_efficiency_exceeded_transitions_entry_to_stale(self, tmp_path: Path) -> None:
        """When slot-efficiency threshold is exceeded after didnt_use increment, state→stale."""
        from owlbear_memory.engine import STALE_THRESHOLD  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        # didnt_use_count = STALE_THRESHOLD: after +1 → STALE_THRESHOLD+1 > STALE_THRESHOLD*1 → stale
        entry = _make_entry(
            _ID_APPROVED,
            "approved",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=STALE_THRESHOLD,
        )
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "didnt_use")
        assert updated.state == MemoryState.STALE

    def test_slot_efficiency_not_exceeded_state_unchanged(self, tmp_path: Path) -> None:
        """When slot-efficiency is not exceeded, entry state remains approved after didnt_use."""
        engine = MemoryEngine(memory_dir=tmp_path)
        # outstanding_count=10 → denominator=10 → threshold=500; didnt_use=1 < 500 → no stale
        entry = _make_entry(
            _ID_APPROVED,
            "approved",
            outstanding_count=10,
            unremarkable_count=0,
            didnt_use_count=1,
        )
        _seed_entry(tmp_path, entry)
        engine.load()

        updated = engine.record_assessment(_ID_APPROVED, "didnt_use")
        assert updated.state == MemoryState.APPROVED

    def test_counter_persisted_to_disk_after_increment(self, tmp_path: Path) -> None:
        """Updated counter is durable: visible when reading via a fresh engine instance."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()

        engine.record_assessment(_ID_APPROVED, "outstanding")

        fresh_engine = MemoryEngine(memory_dir=tmp_path)
        persisted = fresh_engine.get_entry(_ID_APPROVED)
        assert persisted.outstanding_count == 1


# ---------------------------------------------------------------------------
# AC3 — Factually-wrong path
# ---------------------------------------------------------------------------


class TestFactuallyWrongPath:
    """AC3: factually_wrong bucket delegates to record_factually_wrong; no counter/score side effects."""

    @pytest.mark.asyncio
    async def test_factually_wrong_transitions_approved_to_contested(self, tmp_path: Path) -> None:
        """factually_wrong assessment on an approved entry transitions state to contested."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_APPROVED, "bucket": "factually_wrong"}],
            task_id="task-99",
        )

        updated = engine.get_entry(_ID_APPROVED)
        assert updated.state == MemoryState.CONTESTED

    @pytest.mark.asyncio
    async def test_factually_wrong_does_not_increment_any_counter(self, tmp_path: Path) -> None:
        """factually_wrong does not change outstanding/unremarkable/didnt_use counters."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(
            _ID_APPROVED,
            "approved",
            outstanding_count=3,
            unremarkable_count=1,
            didnt_use_count=2,
        )
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_APPROVED, "bucket": "factually_wrong"}],
            task_id="task-99",
        )

        updated = engine.get_entry(_ID_APPROVED)
        assert updated.outstanding_count == 3
        assert updated.unremarkable_count == 1
        assert updated.didnt_use_count == 2

    @pytest.mark.asyncio
    async def test_factually_wrong_does_not_change_score(self, tmp_path: Path) -> None:
        """factually_wrong does not recompute or change the score field."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        initial_score = 0.95
        entry = _make_entry(_ID_APPROVED, "approved", score=initial_score)
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_APPROVED, "bucket": "factually_wrong"}],
            task_id="task-99",
        )

        updated = engine.get_entry(_ID_APPROVED)
        assert updated.score == pytest.approx(initial_score)

    @pytest.mark.asyncio
    async def test_factually_wrong_delegates_to_record_factually_wrong_with_task_id(self, tmp_path: Path) -> None:
        """assess_memories calls record_factually_wrong with the supplied task_id."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        with patch.object(engine, "record_factually_wrong", wraps=engine.record_factually_wrong) as mock_fw:
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": "factually_wrong"}],
                task_id="task-sentinel-abc",
            )

        mock_fw.assert_called_once()
        all_args = list(mock_fw.call_args.args) + list(mock_fw.call_args.kwargs.values())
        assert "task-sentinel-abc" in all_args

    @pytest.mark.asyncio
    async def test_factually_wrong_passes_entry_updated_at_as_expected_updated_at(self, tmp_path: Path) -> None:
        """assess_memories passes entry.updated_at as expected_updated_at to record_factually_wrong."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", updated_at=_TS)
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        with patch.object(engine, "record_factually_wrong", wraps=engine.record_factually_wrong) as mock_fw:
            await assess_memories(
                ctx,
                assessments=[{"entry_id": _ID_APPROVED, "bucket": "factually_wrong"}],
                task_id="task-1",
            )

        all_args = list(mock_fw.call_args.args) + list(mock_fw.call_args.kwargs.values())
        assert _TS in all_args, f"expected_updated_at={_TS!r} was not passed to record_factually_wrong; got: {all_args}"

    @pytest.mark.asyncio
    async def test_factually_wrong_non_voteable_produces_per_item_failure(self, tmp_path: Path) -> None:
        """factually_wrong on non-voteable (pending) produces failure; other items in batch continue."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        pending_entry = _make_entry(_ID_PENDING, "pending")
        approved_entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, pending_entry)
        _seed_entry(tmp_path, approved_entry)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[
                {"entry_id": _ID_PENDING, "bucket": "factually_wrong"},
                {"entry_id": _ID_APPROVED, "bucket": "outstanding"},
            ],
            task_id="task-1",
        )

        results = result["results"]
        pending_result = next(r for r in results if r["entry_id"] == _ID_PENDING)
        approved_result = next(r for r in results if r["entry_id"] == _ID_APPROVED)

        assert pending_result["success"] is False
        assert approved_result["success"] is True


# ---------------------------------------------------------------------------
# AC4 — Batch semantics and per-entry result shape
# ---------------------------------------------------------------------------


class TestBatchSemantics:
    """AC4: per-entry result format, per-item failure, batch-continues, persistence."""

    @pytest.mark.asyncio
    async def test_return_value_has_results_key(self, tmp_path: Path) -> None:
        """Return value is a dict containing a 'results' key."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_APPROVED, "bucket": "outstanding"}],
            task_id="task-1",
        )

        assert isinstance(result, dict)
        assert "results" in result

    @pytest.mark.asyncio
    async def test_success_result_has_entry_id_and_success_true(self, tmp_path: Path) -> None:
        """Successful result contains entry_id and success=True."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_APPROVED, "bucket": "outstanding"}],
            task_id="task-1",
        )

        results = result["results"]
        assert len(results) == 1
        assert results[0]["entry_id"] == _ID_APPROVED
        assert results[0]["success"] is True

    @pytest.mark.asyncio
    async def test_results_list_length_equals_assessments_count(self, tmp_path: Path) -> None:
        """results list has exactly one element per assessment input item."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry1 = _make_entry(_ID_APPROVED, "approved")
        entry2 = _make_entry(_ID_CURATED, "curated")
        _seed_entry(tmp_path, entry1)
        _seed_entry(tmp_path, entry2)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[
                {"entry_id": _ID_APPROVED, "bucket": "outstanding"},
                {"entry_id": _ID_CURATED, "bucket": "unremarkable"},
            ],
            task_id="task-1",
        )

        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_entry_produces_failure_with_error_message(self, tmp_path: Path) -> None:
        """Non-existent entry_id produces failure result with success=False and non-empty error."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_MISSING, "bucket": "outstanding"}],
            task_id="task-1",
        )

        results = result["results"]
        assert len(results) == 1
        assert results[0]["entry_id"] == _ID_MISSING
        assert results[0]["success"] is False
        assert "error" in results[0]
        assert results[0]["error"]  # non-empty

    @pytest.mark.asyncio
    async def test_non_voteable_state_produces_per_item_failure(self, tmp_path: Path) -> None:
        """Non-voteable state (pending) produces failure result with success=False."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_PENDING, "pending")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_PENDING, "bucket": "outstanding"}],
            task_id="task-1",
        )

        results = result["results"]
        assert results[0]["entry_id"] == _ID_PENDING
        assert results[0]["success"] is False
        assert "error" in results[0]

    @pytest.mark.asyncio
    async def test_concurrency_error_produces_per_item_failure(self, tmp_path: Path) -> None:
        """ConcurrencyError on one item produces failure; other items in batch continue."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        approved = _make_entry(_ID_APPROVED, "approved")
        curated = _make_entry(_ID_CURATED, "curated")
        _seed_entry(tmp_path, approved)
        _seed_entry(tmp_path, curated)
        engine.load()

        original_record = engine.record_assessment

        def _patched_record(entry_id: str, bucket: str, expected_updated_at: str | None = None) -> MemoryEntry:
            if entry_id == _ID_APPROVED:
                msg = "simulated OCC conflict"
                raise ConcurrencyError(msg)
            return original_record(entry_id, bucket, expected_updated_at)

        ctx = _make_ctx(engine)
        with patch.object(engine, "record_assessment", side_effect=_patched_record):
            result = await assess_memories(
                ctx,
                assessments=[
                    {"entry_id": _ID_APPROVED, "bucket": "outstanding"},
                    {"entry_id": _ID_CURATED, "bucket": "unremarkable"},
                ],
                task_id="task-1",
            )

        results = result["results"]
        approved_result = next(r for r in results if r["entry_id"] == _ID_APPROVED)
        curated_result = next(r for r in results if r["entry_id"] == _ID_CURATED)

        assert approved_result["success"] is False
        assert "error" in approved_result
        assert curated_result["success"] is True

    @pytest.mark.asyncio
    async def test_one_per_item_failure_does_not_abort_remaining_assessments(self, tmp_path: Path) -> None:
        """A missing entry failure does not abort processing of subsequent valid entries."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved")
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[
                {"entry_id": _ID_MISSING, "bucket": "outstanding"},  # fails
                {"entry_id": _ID_APPROVED, "bucket": "outstanding"},  # must still run
            ],
            task_id="task-1",
        )

        results = result["results"]
        assert len(results) == 2

        missing_result = next(r for r in results if r["entry_id"] == _ID_MISSING)
        approved_result = next(r for r in results if r["entry_id"] == _ID_APPROVED)

        assert missing_result["success"] is False
        assert approved_result["success"] is True

    @pytest.mark.asyncio
    async def test_successful_assessment_persisted_to_disk(self, tmp_path: Path) -> None:
        """Successful counter increment is durable: visible via a fresh engine instance."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_APPROVED, "approved", outstanding_count=0)
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_APPROVED, "bucket": "outstanding"}],
            task_id="task-1",
        )

        fresh_engine = MemoryEngine(memory_dir=tmp_path)
        persisted = fresh_engine.get_entry(_ID_APPROVED)
        assert persisted.outstanding_count == 1

    @pytest.mark.asyncio
    async def test_failed_entry_leaves_disk_state_unchanged(self, tmp_path: Path) -> None:
        """Per-item failure (non-voteable) leaves disk entry unmodified."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(_ID_PENDING, "pending", outstanding_count=0)
        _seed_entry(tmp_path, entry)
        engine.load()
        ctx = _make_ctx(engine)

        await assess_memories(
            ctx,
            assessments=[{"entry_id": _ID_PENDING, "bucket": "outstanding"}],
            task_id="task-1",
        )

        fresh_engine = MemoryEngine(memory_dir=tmp_path)
        persisted = fresh_engine.get_entry(_ID_PENDING)
        assert persisted.outstanding_count == 0
        assert persisted.state == MemoryState.PENDING

    @pytest.mark.asyncio
    async def test_mixed_batch_partial_success_all_results_returned(self, tmp_path: Path) -> None:
        """Mixed batch (one missing, one valid) returns results for both entries."""
        from owlbear_memory_mcp.tools import assess_memories  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        approved = _make_entry(_ID_APPROVED, "approved")
        curated = _make_entry(_ID_CURATED, "curated")
        _seed_entry(tmp_path, approved)
        _seed_entry(tmp_path, curated)
        engine.load()
        ctx = _make_ctx(engine)

        result = await assess_memories(
            ctx,
            assessments=[
                {"entry_id": _ID_MISSING, "bucket": "outstanding"},
                {"entry_id": _ID_APPROVED, "bucket": "outstanding"},
                {"entry_id": _ID_CURATED, "bucket": "unremarkable"},
            ],
            task_id="task-1",
        )

        results = result["results"]
        assert len(results) == 3

        by_id = {r["entry_id"]: r for r in results}
        assert by_id[_ID_MISSING]["success"] is False
        assert by_id[_ID_APPROVED]["success"] is True
        assert by_id[_ID_CURATED]["success"] is True
