"""RED-phase tests for #1839 — Memory voting: forced assessment scoring.

Parent-task AC coverage (cross-cutting behavioral contract):

- AC1: score float field; Score = confidence + (outstanding*0.1) - (unremarkable*0.01);
       recall sorts by (state_rank, -score, id); X=0.1 and Y=0.01 are named constants.
- AC2: assess_memories MCP tool: batch [{entry_id, bucket}], buckets in
       {outstanding, unremarkable, didnt_use, factually_wrong}; updates counters+score
       atomically; returns success/failure per entry; validates entry, state, bucket.
- AC3: recall_memory: default 20 entries; (limit-4) regular + 2 explore + 2 challenge;
       dedup: explore > challenge > regular; fewer entries than limit -> return all.
- AC4: assess_memories triggers stale when didnt_use > 50 * max(outstanding+unremarkable,1);
       stale excluded from recall.
- AC5: first factually_wrong -> contested (still recalled); second from different task_id
       -> disputed (excluded from recall).
- AC6: contested in recall; disputed not in recall; stale not in recall; all resolvable by curator.
- AC7: migrate_scores: score=confidence, counters=0; idempotent; sort order identical.
- AC8: pipeline instruction (docs) -- no testable Python interface; covered by #1847.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState
from owlbear_memory import storage
from owlbear_memory.engine import (
    OUTSTANDING_BOOST,
    STALE_THRESHOLD,
    UNREMARKABLE_PENALTY,
    check_slot_efficiency,
    compute_score,
)
from owlbear_mcp_memory.tools import (
    SLOT_CHALLENGE,
    SLOT_EXPLORE,
    assess_memories,
    recall_memory,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_TS = "2026-01-01T00:00:00+00:00"
_TS_APPROVED = "2026-01-01T01:00:00+00:00"
_AGENT = "scoring-test-agent"
_TASK_A = "task-alpha-1839"
_TASK_B = "task-beta-1839"

_ID_A = "550e8400-e29b-41d4-a716-446655491001"
_ID_B = "550e8400-e29b-41d4-a716-446655491002"
_ID_C = "550e8400-e29b-41d4-a716-446655491003"
_ID_D = "550e8400-e29b-41d4-a716-446655491004"
_ID_E = "550e8400-e29b-41d4-a716-446655491005"

_LEG_A = "550e8400-e29b-41d4-a716-446655492001"
_LEG_B = "550e8400-e29b-41d4-a716-446655492002"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


def _seed(  # noqa: PLR0913
    directory: Path,
    entry_id: str,
    *,
    title: str = "Test Entry",
    confidence: float = 0.8,
    state: MemoryState = MemoryState.APPROVED,
    outstanding_count: int = 0,
    unremarkable_count: int = 0,
    didnt_use_count: int = 0,
    score: float | None = None,
    scope_agents: list[str] | None = None,
    contested_by_task: str | None = None,
) -> MemoryEntry:
    """Write an entry directly to disk at a fixed state."""
    entry = MemoryEntry(
        id=entry_id,
        title=title,
        content=f"Content: {title}.",
        categories=["domain-knowledge"],
        confidence=confidence,
        state=state,
        outstanding_count=outstanding_count,
        unremarkable_count=unremarkable_count,
        didnt_use_count=didnt_use_count,
        score=score if score is not None else confidence,
        scope_agents=scope_agents if scope_agents is not None else [_AGENT],
        source_agent=_AGENT,
        created_at=_TS,
        updated_at=_TS,
        approved_at=_TS_APPROVED if state == MemoryState.APPROVED else None,
        contested_by_task=contested_by_task,
    )
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return entry


def _write_legacy_entry(
    directory: Path,
    entry_id: str,
    title: str,
    confidence: float,
    state: str = "approved",
) -> None:
    """Write a legacy entry WITHOUT score/counter frontmatter fields."""
    approved_at_line = f"approved_at: '{_TS_APPROVED}'" if state == "approved" else "approved_at: null"
    content = (
        "---\n"
        f"id: {entry_id}\n"
        f"title: '{title}'\n"
        "categories:\n"
        "- domain-knowledge\n"
        f"confidence: {confidence}\n"
        f"state: {state}\n"
        "scope_agents:\n"
        f"- {_AGENT}\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{_TS}'\n"
        f"{approved_at_line}\n"
        "contested_by_task: null\n"
        "---\n\n"
        f"Legacy content: {title}.\n"
    )
    (directory / f"{entry_id}.md").write_text(content, encoding="utf-8")


def _loaded(engine: MemoryEngine, entry_id: str) -> MemoryEntry:
    """Force reload and return entry by id."""
    engine.load()
    return engine.get_entry(entry_id)


# ---------------------------------------------------------------------------
# AC1 — Score field, named constants, recall sort
# ---------------------------------------------------------------------------


class TestFromAC_ScoringAndConstants:
    """AC1: score float field; named constants X=0.1, Y=0.01; recall sort by (rank,-score,id)."""

    def test_outstanding_boost_constant_is_0_1(self) -> None:
        """OUTSTANDING_BOOST constant equals 0.1 (named constant X from AC1)."""
        assert OUTSTANDING_BOOST == 0.1

    def test_unremarkable_penalty_constant_is_0_01(self) -> None:
        """UNREMARKABLE_PENALTY constant equals 0.01 (named constant Y from AC1)."""
        assert UNREMARKABLE_PENALTY == 0.01

    def test_stale_threshold_constant_is_50(self) -> None:
        """STALE_THRESHOLD constant equals 50 (required by AC4 formula)."""
        assert STALE_THRESHOLD == 50

    def test_score_field_exists_on_memory_entry(self) -> None:
        """MemoryEntry model includes a 'score' float field."""
        entry = MemoryEntry(
            id=_ID_A,
            title="Test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.8,
            source_agent=_AGENT,
            created_at=_TS,
            updated_at=_TS,
        )
        assert hasattr(entry, "score")
        assert isinstance(entry.score, float)

    def test_score_initialized_to_confidence_on_save(self, tmp_path: Path) -> None:
        """MemoryEngine.save() sets score=confidence (not 0) on a new entry."""
        engine = MemoryEngine(tmp_path)
        entry = engine.save(
            title="Score init",
            content="Content.",
            categories=["process"],
            confidence=0.85,
            source_agent=_AGENT,
            scope_agents=[_AGENT],
        )
        assert entry.score == pytest.approx(0.85)

    def test_compute_score_outstanding_increases_score(self) -> None:
        """compute_score: each outstanding raises score by OUTSTANDING_BOOST (0.1)."""
        base = compute_score(0.8, 0, 0)
        with_one = compute_score(0.8, 1, 0)
        assert with_one == pytest.approx(base + OUTSTANDING_BOOST)

    def test_compute_score_unremarkable_decreases_score(self) -> None:
        """compute_score: each unremarkable lowers score by UNREMARKABLE_PENALTY (0.01)."""
        base = compute_score(0.8, 0, 0)
        with_one = compute_score(0.8, 0, 1)
        assert with_one == pytest.approx(base - UNREMARKABLE_PENALTY)

    def test_compute_score_full_formula(self) -> None:
        """compute_score(0.8, 3, 5) == 0.8 + 3*0.1 - 5*0.01 = 1.05."""
        result = compute_score(0.8, 3, 5)
        assert result == pytest.approx(0.8 + 3 * 0.1 - 5 * 0.01)

    @pytest.mark.asyncio
    async def test_recall_sorts_higher_score_first(self, tmp_path: Path) -> None:
        """recall_memory output lists higher-score entry before lower-score entry."""
        _seed(tmp_path, _ID_A, title="High Score", confidence=0.8, score=0.9)
        _seed(tmp_path, _ID_B, title="Low Score", confidence=0.8, score=0.7)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert isinstance(result, str)
        hi_pos = result.index("High Score")
        lo_pos = result.index("Low Score")
        assert hi_pos < lo_pos


# ---------------------------------------------------------------------------
# AC2 — assess_memories MCP tool contract
# ---------------------------------------------------------------------------


class TestFromAC_AssessMemoriesContract:
    """AC2: assess_memories batch tool — validation, counter updates, per-entry results."""

    @pytest.mark.asyncio
    async def test_batch_result_structure_has_results_key(self, tmp_path: Path) -> None:
        """assess_memories returns dict with 'results' key containing a list."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await assess_memories(ctx, assessments=[{"entry_id": _ID_A, "bucket": "outstanding"}], task_id=_TASK_A)
        assert "results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_success_result_has_entry_id_and_success_true(self, tmp_path: Path) -> None:
        """Successful assessment result has entry_id and success=True."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await assess_memories(ctx, assessments=[{"entry_id": _ID_A, "bucket": "unremarkable"}], task_id=_TASK_A)
        item = result["results"][0]
        assert item["entry_id"] == _ID_A
        assert item["success"] is True

    @pytest.mark.asyncio
    async def test_failure_result_has_entry_id_success_false_and_error(self, tmp_path: Path) -> None:
        """Non-voteable entry result has entry_id, success=False, and error string."""
        _seed(tmp_path, _ID_A, state=MemoryState.PENDING)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await assess_memories(ctx, assessments=[{"entry_id": _ID_A, "bucket": "outstanding"}], task_id=_TASK_A)
        item = result["results"][0]
        assert item["entry_id"] == _ID_A
        assert item["success"] is False
        assert "error" in item
        assert isinstance(item["error"], str)

    @pytest.mark.asyncio
    async def test_batch_continues_after_per_entry_failure(self, tmp_path: Path) -> None:
        """A failed entry does not abort the batch; subsequent entries are processed."""
        _seed(tmp_path, _ID_A, state=MemoryState.PENDING)   # will fail
        _seed(tmp_path, _ID_B, state=MemoryState.APPROVED)  # should succeed
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await assess_memories(
            ctx,
            assessments=[
                {"entry_id": _ID_A, "bucket": "outstanding"},
                {"entry_id": _ID_B, "bucket": "outstanding"},
            ],
            task_id=_TASK_A,
        )
        items = {r["entry_id"]: r for r in result["results"]}
        assert items[_ID_A]["success"] is False
        assert items[_ID_B]["success"] is True

    @pytest.mark.asyncio
    async def test_empty_assessments_raises_tool_error(self, tmp_path: Path) -> None:
        """assess_memories raises ToolError for an empty assessments list."""
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        with pytest.raises(ToolError):
            await assess_memories(ctx, assessments=[], task_id=_TASK_A)

    @pytest.mark.asyncio
    async def test_empty_task_id_raises_tool_error(self, tmp_path: Path) -> None:
        """assess_memories raises ToolError for empty task_id."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        with pytest.raises(ToolError):
            await assess_memories(ctx, assessments=[{"entry_id": _ID_A, "bucket": "outstanding"}], task_id="")

    @pytest.mark.asyncio
    async def test_invalid_bucket_raises_tool_error(self, tmp_path: Path) -> None:
        """assess_memories raises ToolError when any bucket value is invalid."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        with pytest.raises(ToolError):
            await assess_memories(
                ctx, assessments=[{"entry_id": _ID_A, "bucket": "invalid-bucket"}], task_id=_TASK_A
            )

    @pytest.mark.asyncio
    async def test_assess_outstanding_increments_counter_and_updates_score(self, tmp_path: Path) -> None:
        """outstanding bucket increments outstanding_count and recomputes score."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED, confidence=0.8)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        await assess_memories(ctx, assessments=[{"entry_id": _ID_A, "bucket": "outstanding"}], task_id=_TASK_A)
        after = _loaded(engine, _ID_A)
        assert after.outstanding_count == 1
        assert after.score == pytest.approx(0.8 + OUTSTANDING_BOOST)

    @pytest.mark.asyncio
    async def test_contested_entry_is_voteable_state(self, tmp_path: Path) -> None:
        """Contested state is a voteable state for assess_memories."""
        _seed(tmp_path, _ID_A, state=MemoryState.CONTESTED, contested_by_task=_TASK_B)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await assess_memories(ctx, assessments=[{"entry_id": _ID_A, "bucket": "unremarkable"}], task_id=_TASK_A)
        assert result["results"][0]["success"] is True


# ---------------------------------------------------------------------------
# AC3 — recall_memory slot allocation and dedup
# ---------------------------------------------------------------------------


class TestFromAC_RecallSlotAllocation:
    """AC3: recall_memory 16+2+2 slots; dedup explore>challenge>regular; all when fewer than limit."""

    @pytest.mark.asyncio
    async def test_recall_returns_string(self, tmp_path: Path) -> None:
        """recall_memory returns a string (formatted recall text, not a list)."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_default_limit_is_20(self, tmp_path: Path) -> None:
        """recall_memory with limit=None returns at most 20 entries (default limit)."""
        for i in range(25):
            _seed(tmp_path, f"550e8400-e29b-41d4-a716-44665549{i:04d}", state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT, limit=None)
        titles = [line[3:].strip() for line in result.splitlines() if line.startswith("## ")]
        assert len(titles) == 20

    @pytest.mark.asyncio
    async def test_fewer_entries_than_limit_returns_all(self, tmp_path: Path) -> None:
        """When fewer entries exist than limit, all recallable entries are returned."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED, title="Alpha")
        _seed(tmp_path, _ID_B, state=MemoryState.APPROVED, title="Beta")
        _seed(tmp_path, _ID_C, state=MemoryState.APPROVED, title="Gamma")
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT, limit=20)
        titles = [line[3:].strip() for line in result.splitlines() if line.startswith("## ")]
        assert len(titles) == 3

    def test_slot_constants_explore_plus_challenge_equals_four(self) -> None:
        """SLOT_EXPLORE + SLOT_CHALLENGE == 4 — matching the limit-4 regular capacity in AC3."""
        assert SLOT_EXPLORE + SLOT_CHALLENGE == 4

    @pytest.mark.asyncio
    async def test_explore_dedup_excludes_entry_from_challenge_pool(self, tmp_path: Path) -> None:
        """An entry selected into explore is not also selected into challenge (dedup: explore > challenge)."""
        # Entries with all-zero counters qualify for BOTH explore (lowest total) AND
        # challenge (lowest outstanding). They must land in explore, not challenge.
        # We verify by using 2 zero-counter entries (max explore slots) and 2 with
        # outstanding=1 (challenge candidates). Challenge must draw from the latter two.
        _seed(tmp_path, _ID_A, title="ZeroAll A", outstanding_count=0, unremarkable_count=0, didnt_use_count=0, state=MemoryState.APPROVED)
        _seed(tmp_path, _ID_B, title="ZeroAll B", outstanding_count=0, unremarkable_count=0, didnt_use_count=0, state=MemoryState.APPROVED)
        _seed(tmp_path, _ID_C, title="OneOut C", outstanding_count=1, unremarkable_count=0, didnt_use_count=0, state=MemoryState.APPROVED)
        _seed(tmp_path, _ID_D, title="OneOut D", outstanding_count=1, unremarkable_count=0, didnt_use_count=0, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT, limit=4)
        # All 4 entries must appear (total = explore 2 + challenge 2 + regular 0)
        titles = [line[3:].strip() for line in result.splitlines() if line.startswith("## ")]
        assert len(titles) == 4
        assert "ZeroAll A" in titles
        assert "ZeroAll B" in titles
        assert "OneOut C" in titles
        assert "OneOut D" in titles


# ---------------------------------------------------------------------------
# AC4 — Slot-efficiency stale transition
# ---------------------------------------------------------------------------


class TestFromAC_SlotEfficiencyStale:
    """AC4: didnt_use > 50 * max(outstanding+unremarkable, 1) -> stale; stale excluded from recall."""

    def test_stale_fires_when_didnt_use_exceeds_threshold(self) -> None:
        """check_slot_efficiency: 51 didnt_use with 0 outstanding+unremarkable → True (stale)."""
        entry = MemoryEntry(
            id=_ID_A,
            title="Test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.8,
            state=MemoryState.APPROVED,
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=51,
            score=0.8,
            scope_agents=[_AGENT],
            source_agent=_AGENT,
            created_at=_TS,
            updated_at=_TS,
        )
        # denominator = max(0+0, 1) = 1; 51 > 50 * 1 = 50 → True
        assert check_slot_efficiency(entry) is True

    def test_stale_does_not_fire_at_exact_threshold(self) -> None:
        """check_slot_efficiency: 50 didnt_use with 0+0 → False (exactly at threshold, not exceeding)."""
        entry = MemoryEntry(
            id=_ID_A,
            title="Test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.8,
            state=MemoryState.APPROVED,
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=50,
            score=0.8,
            scope_agents=[_AGENT],
            source_agent=_AGENT,
            created_at=_TS,
            updated_at=_TS,
        )
        # denominator = max(0+0, 1) = 1; 50 > 50 * 1 = 50 → False
        assert check_slot_efficiency(entry) is False

    def test_stale_denominator_uses_max_with_one_when_both_counters_zero(self) -> None:
        """max(outstanding+unremarkable, 1) protects denominator when both are 0 (no division by 0)."""
        entry_0 = MemoryEntry(
            id=_ID_A, title="T", content="C.", categories=["domain-knowledge"],
            confidence=0.8, state=MemoryState.APPROVED,
            outstanding_count=0, unremarkable_count=0, didnt_use_count=1,
            score=0.8, scope_agents=[_AGENT], source_agent=_AGENT,
            created_at=_TS, updated_at=_TS,
        )
        entry_1 = MemoryEntry(
            id=_ID_B, title="T", content="C.", categories=["domain-knowledge"],
            confidence=0.8, state=MemoryState.APPROVED,
            outstanding_count=1, unremarkable_count=0, didnt_use_count=1,
            score=0.8, scope_agents=[_AGENT], source_agent=_AGENT,
            created_at=_TS, updated_at=_TS,
        )
        # denominator for entry_0 = max(0+0, 1) = 1; 1 > 50 → False
        # denominator for entry_1 = max(1+0, 1) = 1; 1 > 50 → False
        assert check_slot_efficiency(entry_0) is False
        assert check_slot_efficiency(entry_1) is False

    @pytest.mark.asyncio
    async def test_stale_entry_excluded_from_recall(self, tmp_path: Path) -> None:
        """After stale transition, entry does not appear in recall_memory results."""
        _seed(tmp_path, _ID_A, state=MemoryState.STALE, title="Stale Entry")
        _seed(tmp_path, _ID_B, state=MemoryState.APPROVED, title="Active Entry")
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert "Stale Entry" not in result
        assert "Active Entry" in result


# ---------------------------------------------------------------------------
# AC5 — factually_wrong contested/disputed protocol
# ---------------------------------------------------------------------------


class TestFromAC_FactuallyWrongProtocol:
    """AC5: first factually_wrong → contested; second from different task → disputed; same task → no change."""

    def test_first_factually_wrong_transitions_approved_to_contested(self, tmp_path: Path) -> None:
        """record_factually_wrong on approved entry transitions state to contested."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        result = engine.record_factually_wrong(_ID_A, task_id=_TASK_A)
        assert result.state == MemoryState.CONTESTED

    def test_first_factually_wrong_stores_contested_by_task(self, tmp_path: Path) -> None:
        """After first factually_wrong, contested_by_task equals the submitting task_id."""
        _seed(tmp_path, _ID_A, state=MemoryState.APPROVED)
        engine = MemoryEngine(tmp_path)
        result = engine.record_factually_wrong(_ID_A, task_id=_TASK_A)
        assert result.contested_by_task == _TASK_A

    def test_second_factually_wrong_different_task_transitions_to_disputed(self, tmp_path: Path) -> None:
        """Second factually_wrong from a different task_id escalates contested → disputed."""
        _seed(tmp_path, _ID_A, state=MemoryState.CONTESTED, contested_by_task=_TASK_A)
        engine = MemoryEngine(tmp_path)
        result = engine.record_factually_wrong(_ID_A, task_id=_TASK_B)
        assert result.state == MemoryState.DISPUTED

    def test_same_task_id_on_contested_does_not_escalate(self, tmp_path: Path) -> None:
        """Second factually_wrong from the SAME task_id leaves contested entry unchanged."""
        _seed(tmp_path, _ID_A, state=MemoryState.CONTESTED, contested_by_task=_TASK_A)
        engine = MemoryEngine(tmp_path)
        result = engine.record_factually_wrong(_ID_A, task_id=_TASK_A)
        assert result.state == MemoryState.CONTESTED


# ---------------------------------------------------------------------------
# AC6 — State inclusion/exclusion in recall; curator resolution
# ---------------------------------------------------------------------------


class TestFromAC_StateRecallContract:
    """AC6: contested ∈ recall; disputed ∉ recall; stale ∉ recall; all resolvable by curator."""

    @pytest.mark.asyncio
    async def test_contested_entry_appears_in_recall(self, tmp_path: Path) -> None:
        """Contested entry is included in recall_memory results."""
        _seed(tmp_path, _ID_A, state=MemoryState.CONTESTED, title="Contested Entry", contested_by_task=_TASK_A)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert "Contested Entry" in result

    @pytest.mark.asyncio
    async def test_disputed_entry_excluded_from_recall(self, tmp_path: Path) -> None:
        """Disputed entry is excluded from recall_memory results."""
        _seed(tmp_path, _ID_A, state=MemoryState.DISPUTED, title="Disputed Entry", contested_by_task=_TASK_A)
        engine = MemoryEngine(tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert "Disputed Entry" not in result

    @pytest.mark.asyncio
    async def test_resolve_disputed_entry_returns_it_to_recall(self, tmp_path: Path) -> None:
        """resolve() on disputed entry transitions to approved, making it appear in recall."""
        _seed(tmp_path, _ID_A, state=MemoryState.DISPUTED, title="Resolved Entry", contested_by_task=_TASK_A)
        engine = MemoryEngine(tmp_path)
        entry = engine.get_entry(_ID_A)
        engine.resolve(_ID_A, expected_updated_at=entry.updated_at)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert "Resolved Entry" in result

    @pytest.mark.asyncio
    async def test_resolve_stale_entry_returns_it_to_recall(self, tmp_path: Path) -> None:
        """resolve() on stale entry transitions to approved, making it appear in recall."""
        _seed(tmp_path, _ID_A, state=MemoryState.STALE, title="Un-staled Entry")
        engine = MemoryEngine(tmp_path)
        entry = engine.get_entry(_ID_A)
        engine.resolve(_ID_A, expected_updated_at=entry.updated_at)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        assert "Un-staled Entry" in result

    @pytest.mark.asyncio
    async def test_resolve_contested_entry_returns_it_to_regular_recall(self, tmp_path: Path) -> None:
        """resolve() on contested entry transitions to approved with normal recall inclusion."""
        _seed(tmp_path, _ID_A, state=MemoryState.CONTESTED, title="Un-contested Entry", contested_by_task=_TASK_A)
        engine = MemoryEngine(tmp_path)
        entry = engine.get_entry(_ID_A)
        resolved = engine.resolve(_ID_A, expected_updated_at=entry.updated_at)
        assert resolved.state == MemoryState.APPROVED


# ---------------------------------------------------------------------------
# AC7 — Migration contract
# ---------------------------------------------------------------------------


class TestFromAC_MigrationContract:
    """AC7: migrate_scores sets score=confidence, counters=0; idempotent; sort order preserved."""

    def test_migrate_sets_score_equal_to_confidence(self, tmp_path: Path) -> None:
        """migrate_scores() sets score=confidence for legacy entries without score field."""
        _write_legacy_entry(tmp_path, _LEG_A, "Legacy Alpha", confidence=0.75)
        engine = MemoryEngine(tmp_path)
        engine.migrate_scores()
        entry = _loaded(engine, _LEG_A)
        assert entry.score == pytest.approx(0.75)

    def test_migrate_sets_all_counters_to_zero(self, tmp_path: Path) -> None:
        """migrate_scores() sets outstanding, unremarkable, didnt_use counters to 0."""
        _write_legacy_entry(tmp_path, _LEG_A, "Legacy Beta", confidence=0.8)
        engine = MemoryEngine(tmp_path)
        engine.migrate_scores()
        entry = _loaded(engine, _LEG_A)
        assert entry.outstanding_count == 0
        assert entry.unremarkable_count == 0
        assert entry.didnt_use_count == 0

    def test_migrate_is_idempotent(self, tmp_path: Path) -> None:
        """Running migrate_scores() twice: second call migrates 0 (idempotent)."""
        _write_legacy_entry(tmp_path, _LEG_A, "Legacy Gamma", confidence=0.9)
        engine = MemoryEngine(tmp_path)
        first = engine.migrate_scores()
        second = engine.migrate_scores()
        assert first == 1
        assert second == 0

    def test_migrate_sort_order_identical_pre_and_post(self, tmp_path: Path) -> None:
        """Sort by (-score, id) post-migration equals sort by (-confidence, id) pre-migration."""
        _write_legacy_entry(tmp_path, _LEG_A, "Legacy A", confidence=0.9)
        _write_legacy_entry(tmp_path, _LEG_B, "Legacy B", confidence=0.75)
        engine = MemoryEngine(tmp_path)
        pre_entries = engine.get_entries()
        pre_order = [e.id for e in sorted(pre_entries, key=lambda e: (-e.confidence, e.id))]
        engine.migrate_scores()
        post_entries = engine.get_entries()
        post_order = [e.id for e in sorted(post_entries, key=lambda e: (-e.score, e.id))]
        assert pre_order == post_order
