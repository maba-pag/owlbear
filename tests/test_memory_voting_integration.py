"""Durable integration tests for the memory voting pipeline.

Consolidation test verifying the full memory voting pipeline works across its
storage, assessment, and recall boundaries.

Behavioral coverage:
- AC1: Integration test at MemoryEngine+recall_memory level — save->approve->recall
  with >=20 entries, 16+2+2 slot allocation, score formula, counters, recall sort.
- AC2: State transitions end-to-end — factually_wrong->contested (still recalled),
  second factually_wrong from different task->disputed (excluded from recall),
  didnt_use>50xmax(outstanding+unremarkable,1)->stale (excluded from recall).
- AC3: Migration — seed legacy entries (no score/counter fields), migrate_scores(),
  score=confidence and counters=0, sort equivalence, post-migration assessment.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState
from owlbear_memory import storage
from owlbear_memory.engine import compute_score

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_TS = "2026-01-01T00:00:00+00:00"
_TS_APPROVED = "2026-01-01T00:00:00+00:00"
_AGENT = "integration-test-agent"
_TASK_A = "task-alpha"
_TASK_B = "task-beta"

# Fixed UUIDs for AC1/AC2 tests (100-series)
_IDS_BULK = [f"550e8400-e29b-41d4-a716-4466554811{i:02d}" for i in range(22)]

# Fixed UUIDs for score / counter / sort tests (200-series)
_ID_SCORE_A = "550e8400-e29b-41d4-a716-446655482001"
_ID_SCORE_B = "550e8400-e29b-41d4-a716-446655482002"
_ID_SCORE_C = "550e8400-e29b-41d4-a716-446655482003"

# Fixed UUIDs for AC2 state-transition tests (300-series)
_ID_TRANS_A = "550e8400-e29b-41d4-a716-446655483001"
_ID_TRANS_B = "550e8400-e29b-41d4-a716-446655483002"
_ID_STALE_A = "550e8400-e29b-41d4-a716-446655483003"

# Fixed UUIDs for AC3 migration tests (400-series)
_ID_LEG_A = "550e8400-e29b-41d4-a716-446655484001"
_ID_LEG_B = "550e8400-e29b-41d4-a716-446655484002"
_ID_LEG_C = "550e8400-e29b-41d4-a716-446655484003"

# Fixed UUIDs for AC1 slot-split test (500-series)
_ID_SLOT_EXPLORE_0 = "550e8400-e29b-41d4-a716-446655485001"
_ID_SLOT_EXPLORE_1 = "550e8400-e29b-41d4-a716-446655485002"
_ID_SLOT_CHALLENGE_0 = "550e8400-e29b-41d4-a716-446655485003"
_ID_SLOT_CHALLENGE_1 = "550e8400-e29b-41d4-a716-446655485004"
_IDS_SLOT_REG_HIGH = [f"550e8400-e29b-41d4-a716-4466554851{i:02d}" for i in range(16)]
_IDS_SLOT_REG_LOW = [f"550e8400-e29b-41d4-a716-4466554852{i:02d}" for i in range(2)]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_approved_entry(  # noqa: PLR0913
    entry_id: str,
    title: str,
    confidence: float = 0.8,
    outstanding_count: int = 0,
    unremarkable_count: int = 0,
    didnt_use_count: int = 0,
    scope_agents: list[str] | None = None,
    state: MemoryState = MemoryState.APPROVED,
    contested_by_task: str | None = None,
) -> MemoryEntry:
    agents = scope_agents if scope_agents is not None else [_AGENT]
    score = compute_score(confidence, outstanding_count, unremarkable_count)
    approved_at = _TS_APPROVED if state == MemoryState.APPROVED else None
    return MemoryEntry(
        id=entry_id,
        title=title,
        content=f"Content for {title}.",
        categories=["domain-knowledge"],
        confidence=confidence,
        state=state,
        scope_agents=agents,
        source_agent="test-agent",
        created_at=_TS,
        updated_at=_TS,
        approved_at=approved_at,
        outstanding_count=outstanding_count,
        unremarkable_count=unremarkable_count,
        didnt_use_count=didnt_use_count,
        score=score,
        contested_by_task=contested_by_task,
    )


def _write_entry(directory: Path, entry: MemoryEntry) -> None:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


def _write_legacy_entry(  # noqa: PLR0913
    directory: Path,
    entry_id: str,
    title: str,
    confidence: float,
    state: str = "approved",
    scope_agents: list[str] | None = None,
) -> None:
    """Write a legacy memory entry WITHOUT score/counter fields in frontmatter.

    Bypasses storage.write_entry (which always writes all fields) to create
    pre-migration frontmatter missing score, outstanding_count, unremarkable_count,
    and didnt_use_count.
    """
    agents = scope_agents if scope_agents is not None else [_AGENT]
    scope_lines = "\n".join(f"- {a}" for a in agents)
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
        f"{scope_lines}\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{_TS}'\n"
        f"{approved_at_line}\n"
        "contested_by_task: null\n"
        "---\n\n"
        f"Legacy content for {title}.\n"
    )
    (directory / f"{entry_id}.md").write_text(content, encoding="utf-8")


def _recall_titles(result: str) -> list[str]:
    """Extract title tokens from recall_memory output (## {title} headings)."""
    return [line[3:].strip() for line in result.splitlines() if line.startswith("## ")]


# ---------------------------------------------------------------------------
# TestMemoryVotingLifecycle — AC1
# ---------------------------------------------------------------------------


class TestMemoryVotingLifecycle:
    """AC1: Integration test at MemoryEngine+recall_memory level.

    Exercises: save->approve->recall with >=20 entries, 16+2+2 slot allocation,
    score formula, counter tracking, and recall sort after assessment.
    """

    @pytest.mark.asyncio
    async def test_recall_returns_twenty_from_twenty_two_approved(self, tmp_path: Path) -> None:
        """recall_memory with limit=20 returns exactly 20 entries when 22 are approved."""
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        for i, entry_id in enumerate(_IDS_BULK):
            entry = _make_approved_entry(entry_id, f"Bulk Entry {i:02d}")
            _write_entry(tmp_path, entry)

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await recall_memory(ctx, agent=_AGENT, limit=20)

        titles = _recall_titles(result)
        assert len(titles) == 20

    @pytest.mark.asyncio
    async def test_recall_exercises_explore_pool_with_lowest_activity_entries(self, tmp_path: Path) -> None:
        """Explore pool (2 slots) filled by entries with lowest total assessment activity.

        Entry A and B have zero activity; C through V have high total activity.
        A and B must appear in recall result; the pool logic must include them.
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        # Two entries with zero activity → will land in explore pool
        entry_low_a = _make_approved_entry(_ID_SCORE_A, "Low Activity A", confidence=0.7)
        entry_low_b = _make_approved_entry(_ID_SCORE_B, "Low Activity B", confidence=0.7)
        _write_entry(tmp_path, entry_low_a)
        _write_entry(tmp_path, entry_low_b)

        # 20 more entries with high didnt_use activity
        for i, entry_id in enumerate(_IDS_BULK[:20]):
            entry = _make_approved_entry(
                entry_id,
                f"High Activity {i:02d}",
                confidence=0.8,
                didnt_use_count=10,
            )
            _write_entry(tmp_path, entry)

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await recall_memory(ctx, agent=_AGENT, limit=20)
        titles = _recall_titles(result)

        assert "Low Activity A" in titles
        assert "Low Activity B" in titles

    @pytest.mark.asyncio
    async def test_recall_exercises_challenge_pool_with_lowest_outstanding_entries(self, tmp_path: Path) -> None:
        """Challenge pool (2 slots) filled by entries with lowest outstanding_count not in explore pool.

        Two entries have zero outstanding but non-zero didnt_use → excluded from explore by tiebreak.
        Twenty entries have high outstanding → go to regular pool.
        The zero-outstanding entries appear in challenge pool.
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        # Give these two entries some total activity (didnt_use=1) so they're
        # NOT the lowest-activity entries (explore pool gets truly-zero ones).
        # We seed 20 entries with no activity (→ explore candidates by activity=0),
        # but only 2 explore slots available. The next 2 lowest by outstanding=0 go to challenge.
        # Seed 2 entries with outstanding=0, didnt_use=5 (some activity but no outstanding)
        entry_ch_a = _make_approved_entry(
            _ID_SCORE_A, "Challenge A", confidence=0.8, outstanding_count=0, didnt_use_count=5
        )
        entry_ch_b = _make_approved_entry(
            _ID_SCORE_B, "Challenge B", confidence=0.8, outstanding_count=0, didnt_use_count=5
        )
        _write_entry(tmp_path, entry_ch_a)
        _write_entry(tmp_path, entry_ch_b)

        # 20 entries with zero activity → will fill explore pool (only 2 slots)
        # and overflow into regular pool
        for i, entry_id in enumerate(_IDS_BULK[:20]):
            entry = _make_approved_entry(
                entry_id,
                f"Zero Activity {i:02d}",
                confidence=0.8,
                outstanding_count=3,  # high outstanding → go to regular pool
            )
            _write_entry(tmp_path, entry)

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await recall_memory(ctx, agent=_AGENT, limit=20)
        titles = _recall_titles(result)

        assert "Challenge A" in titles
        assert "Challenge B" in titles

    def test_score_formula_confidence_plus_outstanding_minus_unremarkable(self, tmp_path: Path) -> None:
        """score = confidence + (outstanding x 0.1) - (unremarkable x 0.01) exactly."""
        entry = _make_approved_entry(_ID_SCORE_A, "Score Test", confidence=0.8)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        # 3 outstanding, 2 unremarkable
        entry = engine.record_assessment(_ID_SCORE_A, "outstanding")
        entry = engine.record_assessment(_ID_SCORE_A, "outstanding")
        entry = engine.record_assessment(_ID_SCORE_A, "outstanding")
        entry = engine.record_assessment(_ID_SCORE_A, "unremarkable")
        entry = engine.record_assessment(_ID_SCORE_A, "unremarkable")

        expected_score = 0.8 + 3 * 0.1 - 2 * 0.01
        assert entry.score == pytest.approx(expected_score, abs=1e-9)

    def test_counters_track_each_assessment_bucket_independently(self, tmp_path: Path) -> None:
        """outstanding, unremarkable, didnt_use counters increment independently per call."""
        entry = _make_approved_entry(_ID_SCORE_A, "Counter Test")
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.record_assessment(_ID_SCORE_A, "outstanding")
        engine.record_assessment(_ID_SCORE_A, "outstanding")
        engine.record_assessment(_ID_SCORE_A, "unremarkable")
        result = engine.record_assessment(_ID_SCORE_A, "didnt_use")

        assert result.outstanding_count == 2
        assert result.unremarkable_count == 1
        assert result.didnt_use_count == 1

    def test_counters_match_exact_submission_count(self, tmp_path: Path) -> None:
        """After N record_assessment calls per bucket, counters equal N exactly."""
        entry = _make_approved_entry(_ID_SCORE_A, "Counter Exact Test", confidence=0.9)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        for _ in range(5):
            engine.record_assessment(_ID_SCORE_A, "outstanding")
        for _ in range(3):
            engine.record_assessment(_ID_SCORE_A, "unremarkable")
        for _ in range(7):
            engine.record_assessment(_ID_SCORE_A, "didnt_use")

        result = engine.get_entry(_ID_SCORE_A)
        assert result.outstanding_count == 5
        assert result.unremarkable_count == 3
        assert result.didnt_use_count == 7

    @pytest.mark.asyncio
    async def test_recall_sort_reflects_updated_score_after_outstanding_assessment(self, tmp_path: Path) -> None:
        """After outstanding assessments, recall lists higher-scoring entry first.

        Entry A: confidence=0.7, 2 outstanding → score=0.90
        Entry B: confidence=0.8 → score=0.80
        Recall must place A before B.
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        entry_a = _make_approved_entry(_ID_SCORE_A, "High Score After Boost", confidence=0.7)
        entry_b = _make_approved_entry(_ID_SCORE_B, "Medium Confidence No Boost", confidence=0.8)
        _write_entry(tmp_path, entry_a)
        _write_entry(tmp_path, entry_b)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.record_assessment(_ID_SCORE_A, "outstanding")
        engine.record_assessment(_ID_SCORE_A, "outstanding")

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "High Score After Boost" in titles
        assert "Medium Confidence No Boost" in titles
        assert titles.index("High Score After Boost") < titles.index("Medium Confidence No Boost")

    @pytest.mark.asyncio
    async def test_record_factually_wrong_contested_entry_appears_in_recall(self, tmp_path: Path) -> None:
        """record_factually_wrong on approved entry → contested; entry still in recall result."""
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        entry = _make_approved_entry(_ID_SCORE_C, "Contested But Recalled", confidence=0.8)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.record_factually_wrong(_ID_SCORE_C, task_id=_TASK_A)

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "Contested But Recalled" in titles

    @pytest.mark.asyncio
    async def test_full_lifecycle_save_edit_approve_then_recall(self, tmp_path: Path) -> None:
        """AC1 lifecycle proof: entries driven through real save->curated->approved path appear in recall.

        Uses engine.save() + engine.edit(scope_agents=...) + engine.approve() for each
        of 22 entries to exercise the full public API chain (PENDING->CURATED->APPROVED).
        recall_memory with limit=20 must return exactly 20 entries, proving that entries
        created via the real lifecycle are recallable — not a shortcut via direct file write.
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        for i, entry_id in enumerate(_IDS_BULK):
            with patch("owlbear_memory.engine.uuid4", return_value=UUID(entry_id)):
                pending = engine.save(
                    title=f"Lifecycle Entry {i:02d}",
                    content=f"Content {i}.",
                    categories=["domain-knowledge"],
                    confidence=0.8,
                    source_agent=_AGENT,
                    scope_agents=[_AGENT],
                )
            curated = engine.edit(
                pending.id,
                {
                    "title": f"Lifecycle Entry {i:02d}",
                    "content": f"Content {i}.",
                    "categories": ["domain-knowledge"],
                    "confidence": 0.8,
                    "scope_agents": [_AGENT],
                },
                expected_updated_at=pending.updated_at,
            )
            engine.approve(curated.id, expected_updated_at=curated.updated_at)

        result = await recall_memory(ctx, agent=_AGENT, limit=20)
        titles = _recall_titles(result)

        assert len(titles) == 20

    @pytest.mark.asyncio
    async def test_recall_slot_allocation_exactly_16_regular_2_explore_2_challenge(self, tmp_path: Path) -> None:
        """Exact 16+2+2 slot allocation at limit=20 with 22 entries seeded across all three pools.

        Setup:
        - 2 ExploreEntry: total_activity=0 (all counters zero) -> explore pool (2 slots)
        - 2 ChallengeEntry: total_activity=3 (didnt_use=3), outstanding=0 -> challenge pool (2 slots)
        - 16 RegularHigh: outstanding=5, confidence=0.9 -> score=1.4 -> regular pool (top 16, included)
        - 2 RegularLow: outstanding=5, confidence=0.5 -> score=1.0 -> regular candidates, excluded

        The assertions are tight enough that each wrong allocation size causes a failure:
        - explore<2: ExploreEntry displaced by high-activity entries
        - challenge<2: ChallengeEntry displaced by high-outstanding entries
        - regular>16: RegularLow 00/01 appear in results
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        # Explore pool candidates: total activity=0 (lowest _explore_metric)
        for eid, name in [
            (_ID_SLOT_EXPLORE_0, "ExploreEntry 0"),
            (_ID_SLOT_EXPLORE_1, "ExploreEntry 1"),
        ]:
            _write_entry(
                tmp_path,
                _make_approved_entry(eid, name, confidence=0.8, outstanding_count=0),
            )

        # Challenge pool candidates: activity=3 (NOT explore), outstanding=0 (lowest among non-explore)
        for eid, name in [
            (_ID_SLOT_CHALLENGE_0, "ChallengeEntry 0"),
            (_ID_SLOT_CHALLENGE_1, "ChallengeEntry 1"),
        ]:
            _write_entry(
                tmp_path,
                _make_approved_entry(eid, name, confidence=0.8, outstanding_count=0, didnt_use_count=3),
            )

        # 16 high-score regular entries: outstanding=5, confidence=0.9 -> score=1.4
        for i, eid in enumerate(_IDS_SLOT_REG_HIGH):
            _write_entry(
                tmp_path,
                _make_approved_entry(eid, f"RegularHigh {i:02d}", confidence=0.9, outstanding_count=5),
            )

        # 2 low-score regular candidates: outstanding=5, confidence=0.7 -> score=1.2 -> excluded
        # (RegularHigh score=1.4 > RegularLow score=1.2; top 16 slots taken by RegularHigh)
        for i, eid in enumerate(_IDS_SLOT_REG_LOW):
            _write_entry(
                tmp_path,
                _make_approved_entry(eid, f"RegularLow {i:02d}", confidence=0.7, outstanding_count=5),
            )

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT, limit=20)
        titles = _recall_titles(result)

        assert len(titles) == 20

        # Explore pool (2 slots): zero-activity entries must appear
        assert "ExploreEntry 0" in titles
        assert "ExploreEntry 1" in titles

        # Challenge pool (2 slots): zero-outstanding, some-activity entries must appear
        assert "ChallengeEntry 0" in titles
        assert "ChallengeEntry 1" in titles

        # Regular pool (16 slots): all high-score entries included
        for i in range(16):
            assert f"RegularHigh {i:02d}" in titles

        # Regular pool overflow: low-score candidates must be excluded (proves regular<=16)
        assert "RegularLow 00" not in titles
        assert "RegularLow 01" not in titles


# ---------------------------------------------------------------------------
# TestMemoryVotingStateTransitions — AC2
# ---------------------------------------------------------------------------


class TestMemoryVotingStateTransitions:
    """AC2: State transitions verified end-to-end via recall_memory inclusion/exclusion.

    Covers: (a) approved→contested via factually_wrong (included in recall),
    (b) contested→disputed via second factually_wrong different task (excluded),
    (c) approved→stale via check_slot_efficiency (excluded).
    """

    def test_first_factually_wrong_transitions_approved_to_contested(self, tmp_path: Path) -> None:
        """record_factually_wrong on approved entry returns contested state."""
        entry = _make_approved_entry(_ID_TRANS_A, "Will Become Contested")
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.record_factually_wrong(_ID_TRANS_A, task_id=_TASK_A)

        assert result.state == MemoryState.CONTESTED
        assert result.contested_by_task == _TASK_A

    @pytest.mark.asyncio
    async def test_contested_entry_included_in_recall(self, tmp_path: Path) -> None:
        """Contested entry (state=contested) appears in recall_memory result."""
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        entry = _make_approved_entry(
            _ID_TRANS_A,
            "In Recall When Contested",
            state=MemoryState.CONTESTED,
            contested_by_task=_TASK_A,
        )
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "In Recall When Contested" in titles

    def test_second_factually_wrong_different_task_transitions_contested_to_disputed(self, tmp_path: Path) -> None:
        """Second record_factually_wrong from different task_id transitions contested→disputed."""
        entry = _make_approved_entry(_ID_TRANS_A, "Will Become Disputed")
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.record_factually_wrong(_ID_TRANS_A, task_id=_TASK_A)
        result = engine.record_factually_wrong(_ID_TRANS_A, task_id=_TASK_B)

        assert result.state == MemoryState.DISPUTED

    @pytest.mark.asyncio
    async def test_disputed_entry_excluded_from_recall(self, tmp_path: Path) -> None:
        """Disputed entry is excluded from recall_memory result."""
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        entry = _make_approved_entry(
            _ID_TRANS_A,
            "Excluded When Disputed",
            state=MemoryState.DISPUTED,
            contested_by_task=_TASK_B,
        )
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "Excluded When Disputed" not in titles

    def test_full_factually_wrong_pipeline_contested_then_disputed(self, tmp_path: Path) -> None:
        """Full pipeline: approved→contested via task_A, then →disputed via task_B."""
        entry = _make_approved_entry(_ID_TRANS_A, "Pipeline Confirmed")
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        after_first = engine.record_factually_wrong(_ID_TRANS_A, task_id=_TASK_A)
        assert after_first.state == MemoryState.CONTESTED

        after_second = engine.record_factually_wrong(_ID_TRANS_A, task_id=_TASK_B)
        assert after_second.state == MemoryState.DISPUTED

    def test_stale_transition_via_check_slot_efficiency_threshold(self, tmp_path: Path) -> None:
        """Entry transitions to stale when didnt_use > 50 x max(outstanding+unremarkable, 1).

        Threshold: 51 didnt_use with 0 outstanding and 0 unremarkable triggers stale.
        """
        entry = _make_approved_entry(_ID_STALE_A, "Will Become Stale")
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        for _ in range(51):
            result = engine.record_assessment(_ID_STALE_A, "didnt_use")

        assert result.state == MemoryState.STALE

    @pytest.mark.asyncio
    async def test_stale_entry_excluded_from_recall(self, tmp_path: Path) -> None:
        """Stale entry (state=stale) is excluded from recall_memory result."""
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        entry = _make_approved_entry(
            _ID_STALE_A,
            "Excluded When Stale",
            state=MemoryState.STALE,
        )
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "Excluded When Stale" not in titles

    def test_stale_threshold_boundary_at_fifty_not_stale(self, tmp_path: Path) -> None:
        """Exactly 50 didnt_use with 0 outstanding/unremarkable does NOT trigger stale.

        Predicate: didnt_use > 50 x max(outstanding+unremarkable, 1) — must be strictly greater.
        """
        entry = _make_approved_entry(_ID_STALE_A, "At Boundary Not Stale")
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        for _ in range(50):
            result = engine.record_assessment(_ID_STALE_A, "didnt_use")

        assert result.state == MemoryState.APPROVED

    @pytest.mark.asyncio
    async def test_full_state_transition_pipeline_recall_inclusion_exclusion(self, tmp_path: Path) -> None:
        """Integration: three entries cycle through contested/disputed/stale; recall reflects each.

        Entry A: approved → contested → still in recall
        Entry B: approved → contested → disputed → excluded from recall
        Entry C: approved → stale (via 51 didnt_use) → excluded from recall
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        entry_a = _make_approved_entry(_ID_TRANS_A, "Entry A Contested")
        entry_b = _make_approved_entry(_ID_TRANS_B, "Entry B Disputed")
        entry_c = _make_approved_entry(_ID_STALE_A, "Entry C Stale")
        for e in (entry_a, entry_b, entry_c):
            _write_entry(tmp_path, e)

        engine = MemoryEngine(memory_dir=tmp_path)

        # Entry A → contested
        engine.record_factually_wrong(_ID_TRANS_A, task_id=_TASK_A)
        # Entry B → contested → disputed
        engine.record_factually_wrong(_ID_TRANS_B, task_id=_TASK_A)
        engine.record_factually_wrong(_ID_TRANS_B, task_id=_TASK_B)
        # Entry C → stale
        for _ in range(51):
            engine.record_assessment(_ID_STALE_A, "didnt_use")

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "Entry A Contested" in titles
        assert "Entry B Disputed" not in titles
        assert "Entry C Stale" not in titles


# ---------------------------------------------------------------------------
# TestMemoryVotingMigration — AC3
# ---------------------------------------------------------------------------


class TestMemoryVotingMigration:
    """AC3: Migration test — legacy frontmatter without score/counter fields.

    Covers: migrate_scores() sets score=confidence and counters=0;
    sort by (-score, id) equals sort by (-confidence, id) within same state_rank;
    post-migration record_assessment updates score per formula;
    post-migration recall reflects new order.
    """

    def test_migrate_scores_returns_count_of_migrated_entries(self, tmp_path: Path) -> None:
        """migrate_scores() returns the number of legacy entries updated."""
        _write_legacy_entry(tmp_path, _ID_LEG_A, "Legacy A", confidence=0.7)
        _write_legacy_entry(tmp_path, _ID_LEG_B, "Legacy B", confidence=0.8)
        _write_legacy_entry(tmp_path, _ID_LEG_C, "Legacy C", confidence=0.9)
        engine = MemoryEngine(memory_dir=tmp_path)

        migrated = engine.migrate_scores()

        assert migrated == 3

    def test_migrate_scores_sets_score_equal_to_confidence(self, tmp_path: Path) -> None:
        """After migrate_scores(), each entry's score equals its original confidence."""
        _write_legacy_entry(tmp_path, _ID_LEG_A, "Legacy A", confidence=0.7)
        _write_legacy_entry(tmp_path, _ID_LEG_B, "Legacy B", confidence=0.8)
        _write_legacy_entry(tmp_path, _ID_LEG_C, "Legacy C", confidence=0.9)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.migrate_scores()

        entry_a = engine.get_entry(_ID_LEG_A)
        entry_b = engine.get_entry(_ID_LEG_B)
        entry_c = engine.get_entry(_ID_LEG_C)
        assert entry_a.score == pytest.approx(0.7, abs=1e-9)
        assert entry_b.score == pytest.approx(0.8, abs=1e-9)
        assert entry_c.score == pytest.approx(0.9, abs=1e-9)

    def test_migrate_scores_sets_all_counters_to_zero(self, tmp_path: Path) -> None:
        """After migrate_scores(), outstanding, unremarkable, didnt_use counters are all 0."""
        _write_legacy_entry(tmp_path, _ID_LEG_A, "Legacy A", confidence=0.8)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.migrate_scores()

        entry = engine.get_entry(_ID_LEG_A)
        assert entry.outstanding_count == 0
        assert entry.unremarkable_count == 0
        assert entry.didnt_use_count == 0

    def test_migrate_scores_sort_by_score_id_equals_sort_by_confidence_id_within_state_rank(
        self, tmp_path: Path
    ) -> None:
        """Within same state_rank, sort by (-score, id) equals sort by (-confidence, id) post-migration.

        Immediately after migration, score=confidence for all entries; both sort keys must produce
        the same ordering.
        """
        _write_legacy_entry(tmp_path, _ID_LEG_A, "Legacy A", confidence=0.7)
        _write_legacy_entry(tmp_path, _ID_LEG_B, "Legacy B", confidence=0.9)
        _write_legacy_entry(tmp_path, _ID_LEG_C, "Legacy C", confidence=0.8)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.migrate_scores()

        entries = engine.get_entries()
        # Filter to approved state only (same state_rank)
        approved = [e for e in entries if e.state == MemoryState.APPROVED]

        sort_by_score = sorted(approved, key=lambda e: (-e.score, e.id))
        sort_by_confidence = sorted(approved, key=lambda e: (-e.confidence, e.id))

        assert [e.id for e in sort_by_score] == [e.id for e in sort_by_confidence]

    def test_migrate_scores_does_not_migrate_already_modern_entries(self, tmp_path: Path) -> None:
        """migrate_scores() skips entries that already have score/counter fields; returns 0 for them."""
        # Write a modern entry using storage.write_entry (has all fields)
        modern_entry = _make_approved_entry(_ID_LEG_A, "Modern Entry", confidence=0.8)
        _write_entry(tmp_path, modern_entry)

        # Write one legacy entry
        _write_legacy_entry(tmp_path, _ID_LEG_B, "Legacy Only", confidence=0.75)

        engine = MemoryEngine(memory_dir=tmp_path)
        migrated = engine.migrate_scores()

        assert migrated == 1  # Only the legacy entry is migrated

    def test_post_migration_record_assessment_updates_score_per_formula(self, tmp_path: Path) -> None:
        """After migrate_scores(), record_assessment updates score = confidence + outstanding x 0.1."""
        _write_legacy_entry(tmp_path, _ID_LEG_A, "Post-Migration Score", confidence=0.8)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        result = engine.record_assessment(_ID_LEG_A, "outstanding")

        expected_score = 0.8 + 1 * 0.1
        assert result.score == pytest.approx(expected_score, abs=1e-9)
        assert result.outstanding_count == 1

    def test_post_migration_record_assessment_unremarkable_updates_score(self, tmp_path: Path) -> None:
        """After migrate_scores(), record_assessment(unremarkable) adjusts score = confidence - 1 x 0.01."""
        _write_legacy_entry(tmp_path, _ID_LEG_A, "Post-Migration Unremarkable", confidence=0.9)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        result = engine.record_assessment(_ID_LEG_A, "unremarkable")

        expected_score = 0.9 - 1 * 0.01
        assert result.score == pytest.approx(expected_score, abs=1e-9)
        assert result.unremarkable_count == 1

    @pytest.mark.asyncio
    async def test_post_migration_recall_order_reflects_score_after_outstanding(self, tmp_path: Path) -> None:
        """Post-migration: entry with outstanding boost appears first in recall.

        Entry A: confidence=0.75 + 2 outstanding → score=0.95
        Entry B: confidence=0.8 → score=0.8 (migration only)
        recall_memory must list A before B.
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        _write_legacy_entry(tmp_path, _ID_LEG_A, "Boosted After Migration", confidence=0.75)
        _write_legacy_entry(tmp_path, _ID_LEG_B, "Static After Migration", confidence=0.8)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.migrate_scores()

        engine.record_assessment(_ID_LEG_A, "outstanding")
        engine.record_assessment(_ID_LEG_A, "outstanding")

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "Boosted After Migration" in titles
        assert "Static After Migration" in titles
        assert titles.index("Boosted After Migration") < titles.index("Static After Migration")

    @pytest.mark.asyncio
    async def test_migrate_and_recall_full_round_trip(self, tmp_path: Path) -> None:
        """Full AC3 round trip: seed legacy → migrate → assess → recall reflects new order.

        Three legacy entries: A(conf=0.7), B(conf=0.8), C(conf=0.9).
        Post-migration score=confidence for all.
        Apply 3 outstanding to A: 0.7 + 3*0.1 = 1.0 → A.score=1.0 > C.score=0.9 > B.score=0.8.
        Recall order: A, C, B.
        """
        from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

        _write_legacy_entry(tmp_path, _ID_LEG_A, "Legacy Low Conf Boosted", confidence=0.7)
        _write_legacy_entry(tmp_path, _ID_LEG_B, "Legacy Mid Conf Static", confidence=0.8)
        _write_legacy_entry(tmp_path, _ID_LEG_C, "Legacy High Conf Static", confidence=0.9)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.migrate_scores()

        engine.record_assessment(_ID_LEG_A, "outstanding")
        engine.record_assessment(_ID_LEG_A, "outstanding")
        engine.record_assessment(_ID_LEG_A, "outstanding")

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent=_AGENT)
        titles = _recall_titles(result)

        assert "Legacy Low Conf Boosted" in titles
        assert "Legacy High Conf Static" in titles
        assert "Legacy Mid Conf Static" in titles
        assert titles.index("Legacy Low Conf Boosted") < titles.index("Legacy High Conf Static")
        assert titles.index("Legacy High Conf Static") < titles.index("Legacy Mid Conf Static")
