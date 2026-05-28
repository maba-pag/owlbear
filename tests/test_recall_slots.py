"""RED-phase tests for #1843 — P2-04: Recall reserved explore and challenge slots.

AC coverage:
- AC1: max(0, limit-SLOT_EXPLORE-SLOT_CHALLENGE) regular slots; named constants
       SLOT_EXPLORE=2, SLOT_CHALLENGE=2; explore picks lowest total assessment metric;
       challenge picks lowest outstanding_count from remaining; regular picks highest score.
- AC2: limit <= SLOT_EXPLORE+SLOT_CHALLENGE → regular=0; explore fills first (up to limit),
       challenge fills remainder; explore metric = outstanding+unremarkable+didnt_use.
- AC3: Dedup: explore > challenge > regular; entry in explore excluded from challenge pool,
       freeing up the challenge slot for a different entry.
- AC4: Final list sorted by (state_rank, -score, id) regardless of pool origin.
- AC5: Tiebreaker for pool selection: identical metric → lowest id lexicographically.
- AC6: State filter: approved/curated/contested included; disputed/stale/deleted/pending excluded.
       Contested entry can win an explore slot over a high-confidence curated entry.

Design note — test failure strategy:
  The current recall_memory sorts by -confidence (not -score) and has no slot logic.
  Tests that rely on explore/challenge slot selection FAIL because:
    (a) SLOT_EXPLORE / SLOT_CHALLENGE constants do not exist yet, and
    (b) the pool selection algorithm selects by confidence rank, not assessment metric.
  AC5 tiebreak tests are designed so the current confidence-based sort picks a
  different entry than the new id-based tiebreak.
  AC4 sort tests specifically arrange entries so score and confidence disagree.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry
from owlbear_memory import storage

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"
_AGENT = "test-agent"


def _uuid(n: int) -> str:
    """Return a deterministic UUIDv4 string namespaced to task #1843."""
    return f"550e8400-e29b-41d4-a716-44665518{n:04d}"


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


def _write_entry(directory: Path, *, entry_id: str, **overrides: object) -> MemoryEntry:
    """Write a MemoryEntry with explicit field values via storage.write_entry().

    Bypasses the engine save/edit path so score, count fields, and arbitrary
    states can be set directly.  Default: curated, scoped to _AGENT, score=0.85,
    all counts=0.
    """
    defaults: dict[str, object] = {
        "id": entry_id,
        "title": f"Entry-{entry_id[-4:]}",
        "categories": ["domain-knowledge"],
        "confidence": 0.85,
        "state": "curated",
        "content": f"Body of entry {entry_id[-4:]}.",
        "outstanding_count": 0,
        "unremarkable_count": 0,
        "didnt_use_count": 0,
        "score": 0.85,
        "scope_agents": [_AGENT],
        "source_agent": _AGENT,
        "created_at": _TS,
        "updated_at": _TS,
        "approved_at": None,
    }
    defaults.update(overrides)
    entry = MemoryEntry(**defaults)
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return entry


async def _recall(*args: object, **kwargs: object) -> str:
    """Proxy that imports recall_memory at call time.

    Deferred import prevents collection errors if the module hasn't been updated.
    Every call that exercises new slot logic will fail because the implementation
    is not yet in place.
    """
    from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

    return await recall_memory(*args, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFromAC_SlotConstants — AC1
# ---------------------------------------------------------------------------


class TestSlotConstants:
    """AC1: Named constants SLOT_EXPLORE=2, SLOT_CHALLENGE=2 in the tools module.

    recall_memory returns at most limit entries drawn from three pools:
      explore = up to SLOT_EXPLORE entries with the lowest total assessment metric.
      challenge = up to SLOT_CHALLENGE entries with the lowest outstanding_count
                  from the remaining (non-explore) in-scope entries.
      regular = up to max(0, limit - SLOT_EXPLORE - SLOT_CHALLENGE) highest-score
                entries from what remains after explore and challenge dedup.
    """

    def test_slot_explore_constant_equals_2(self) -> None:
        """SLOT_EXPLORE constant exists in owlbear_mcp_memory.tools and equals 2."""
        from owlbear_mcp_memory.tools import SLOT_EXPLORE  # noqa: PLC0415

        assert SLOT_EXPLORE == 2

    def test_slot_challenge_constant_equals_2(self) -> None:
        """SLOT_CHALLENGE constant exists in owlbear_mcp_memory.tools and equals 2."""
        from owlbear_mcp_memory.tools import SLOT_CHALLENGE  # noqa: PLC0415

        assert SLOT_CHALLENGE == 2

    @pytest.mark.asyncio
    async def test_explore_selects_lowest_total_assessment_metric_entries(self, tmp_path: Path) -> None:
        """Explore pool contains the 2 entries with lowest (outstanding+unremarkable+didnt_use).

        Setup: 4 entries ranked by explore metric. limit=2 → only explore fills.
        Current impl (top-2 by -confidence) returns the HIGH-confidence entries;
        new impl (top-2 by lowest metric) returns the LOW-metric entries instead.

        explore metric: E (metric=0) < D (metric=0, lower score but same metric)
          wait — use distinct metrics so ordering is unambiguous.
        Entry A: metric=0, confidence=0.71 → explore pick 1
        Entry B: metric=1, confidence=0.70 → explore pick 2
        Entry C: metric=8, confidence=0.99 → NOT picked (high metric, wins by -confidence currently)
        Entry D: metric=9, confidence=0.98 → NOT picked
        """
        a = _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-A",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.71,
            score=0.71,
        )
        b = _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-B",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.70,
            score=0.70,
        )
        c = _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="High-Conf-C",
            outstanding_count=4,
            unremarkable_count=2,
            didnt_use_count=2,
            confidence=0.99,
            score=0.99,
        )
        d = _write_entry(
            tmp_path,
            entry_id=_uuid(4),
            title="High-Conf-D",
            outstanding_count=5,
            unremarkable_count=2,
            didnt_use_count=2,
            confidence=0.98,
            score=0.98,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=2)

        # New: explore fills both slots → A (metric=0) and B (metric=1)
        assert a.title in result
        assert b.title in result
        # Current impl (top-2 by -confidence) returns C and D instead
        assert c.title not in result
        assert d.title not in result

    @pytest.mark.asyncio
    async def test_challenge_selects_lowest_outstanding_from_remaining_after_dedup(self, tmp_path: Path) -> None:
        """Challenge pool picks 2 entries with lowest outstanding_count from non-explore pool.

        Setup: 6 entries, limit=4 (explore=2, challenge=2, regular=0).
        Explore takes the 2 lowest-metric entries; challenge takes next 2 by outstanding_count
        from the remaining 4; the 2 high-confidence entries are excluded.

        Current impl (top-4 by -confidence) returns the 4 highest-confidence entries,
        which are NOT the challenge picks — so the challenge-specific entries are absent.
        """
        # Explore pool (metric=0 and metric=1, low confidence)
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-1",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.71,
            score=0.71,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-2",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.70,
            score=0.70,
        )
        # Challenge pool (lowest outstanding from remaining 4)
        ch1 = _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Challenge-1",
            outstanding_count=1,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.73,
            score=0.73,
        )
        ch2 = _write_entry(
            tmp_path,
            entry_id=_uuid(4),
            title="Challenge-2",
            outstanding_count=2,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.72,
            score=0.72,
        )
        # High-confidence entries: current top-4 picks these; new impl does NOT
        _write_entry(
            tmp_path,
            entry_id=_uuid(5),
            title="High-Conf-X",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.99,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(6),
            title="High-Conf-Y",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.98,
            score=0.98,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=4)

        # New: challenge=[Challenge-1, Challenge-2]; High-Conf-X and High-Conf-Y not in result
        assert ch1.title in result
        assert ch2.title in result
        assert "High-Conf-X" not in result
        assert "High-Conf-Y" not in result

    @pytest.mark.asyncio
    async def test_regular_pool_takes_highest_score_from_remaining_entries(self, tmp_path: Path) -> None:
        """Regular pool picks max(0, limit-4) entries by highest score after explore+challenge dedup.

        Setup: 8 entries, limit=6 (explore=2, challenge=2, regular=2).
        Regular picks the 2 highest-score entries from the 4 remaining after dedup.
        The 2 highest-confidence (but not highest-score) entries are excluded by slots.
        """
        # Explore picks these (lowest total metric, low confidence)
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-1",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.71,
            score=0.71,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-2",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.70,
            score=0.70,
        )
        # Challenge picks these (lowest outstanding from remaining)
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Challenge-1",
            outstanding_count=1,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.73,
            score=0.73,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(4),
            title="Challenge-2",
            outstanding_count=2,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.72,
            score=0.72,
        )
        # Regular picks top-2 score from remaining (entries 5-8)
        r_hi = _write_entry(
            tmp_path,
            entry_id=_uuid(5),
            title="Regular-HiScore",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.77,
            score=0.98,
        )
        r_lo = _write_entry(
            tmp_path,
            entry_id=_uuid(6),
            title="Regular-LoScore",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.76,
            score=0.90,
        )
        # These two entries are NOT in the result (lower score than r_hi/r_lo, high confidence)
        _write_entry(
            tmp_path,
            entry_id=_uuid(7),
            title="Skip-HighConf-G",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.75,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(8),
            title="Skip-HighConf-H",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.98,
            score=0.74,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=6)

        # Regular pool should contain the two highest-score remaining entries
        assert r_hi.title in result
        assert r_lo.title in result
        # High-confidence but low-score entries must NOT be in result
        assert "Skip-HighConf-G" not in result
        assert "Skip-HighConf-H" not in result


# ---------------------------------------------------------------------------
# TestFromAC_LimitEdge — AC2
# ---------------------------------------------------------------------------


class TestLimitEdge:
    """AC2: limit <= SLOT_EXPLORE + SLOT_CHALLENGE → regular pool is 0.

    Explore fills first (up to limit), challenge fills the remainder.
    Explore metric = outstanding_count + unremarkable_count + didnt_use_count.
    """

    @pytest.mark.asyncio
    async def test_limit_four_regular_pool_is_zero(self, tmp_path: Path) -> None:
        """limit=4 → max(0, 4-2-2)=0 regular slots; all 4 slots are explore+challenge.

        High-confidence (but high-metric) entries are excluded because there is no
        regular pool to absorb them.  Current impl returns them (top-4 by -confidence).
        """
        # Explore and challenge picks (low metric, low confidence)
        for i, total_metric in enumerate([0, 1, 10, 11], start=1):
            _write_entry(
                tmp_path,
                entry_id=_uuid(i),
                title=f"Slot-{i}",
                outstanding_count=total_metric,
                unremarkable_count=0,
                didnt_use_count=0,
                confidence=0.70 + i * 0.01,
                score=0.70 + i * 0.01,
            )
        # High-confidence entries that should NOT appear (no regular pool)
        _write_entry(
            tmp_path,
            entry_id=_uuid(5),
            title="Regular-Would-Be-X",
            outstanding_count=100,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.99,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(6),
            title="Regular-Would-Be-Y",
            outstanding_count=100,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.98,
            score=0.98,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=4)

        assert "Regular-Would-Be-X" not in result
        assert "Regular-Would-Be-Y" not in result
        titles = [line[3:] for line in result.split("\n") if line.startswith("## ")]
        assert len(titles) == 4

    @pytest.mark.asyncio
    async def test_limit_three_explore_gets_two_challenge_gets_one(self, tmp_path: Path) -> None:
        """limit=3 → explore fills 2, challenge fills 1; 4th challenge candidate excluded."""
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-1",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.71,
            score=0.71,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-2",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.70,
            score=0.70,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Challenge-1",
            outstanding_count=1,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.74,
            score=0.74,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(4),
            title="Challenge-2",
            outstanding_count=2,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.73,
            score=0.73,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=3)

        titles = [line[3:] for line in result.split("\n") if line.startswith("## ")]
        assert len(titles) == 3
        assert "Explore-1" in result
        assert "Explore-2" in result
        assert "Challenge-1" in result
        assert "Challenge-2" not in result

    @pytest.mark.asyncio
    async def test_limit_two_explore_fills_all_no_challenge(self, tmp_path: Path) -> None:
        """limit=2 → explore fills both slots; challenge gets 0 entries."""
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-1",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.71,
            score=0.71,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-2",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.70,
            score=0.70,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Challenge-Excluded",
            outstanding_count=1,
            unremarkable_count=5,
            didnt_use_count=5,
            confidence=0.99,
            score=0.99,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=2)

        titles = [line[3:] for line in result.split("\n") if line.startswith("## ")]
        assert len(titles) == 2
        assert "Explore-1" in result
        assert "Explore-2" in result
        assert "Challenge-Excluded" not in result

    @pytest.mark.asyncio
    async def test_limit_one_returns_lowest_metric_entry(self, tmp_path: Path) -> None:
        """limit=1 → a single explore slot; the entry with the lowest total metric wins.

        Current impl picks by highest confidence; new impl picks by lowest metric.
        This test fails when an entry with metric=0 has lower confidence than another.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Metric-Zero",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.70,
            score=0.70,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="High-Conf",
            outstanding_count=5,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.99,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=1)

        assert "Metric-Zero" in result
        assert "High-Conf" not in result

    @pytest.mark.asyncio
    async def test_explore_metric_includes_all_three_counters(self, tmp_path: Path) -> None:
        """Explore metric = outstanding + unremarkable + didnt_use (all three contribute).

        Entry A: outstanding=2, unremarkable=0, didnt_use=0 → metric=2
        Entry B: outstanding=0, unremarkable=1, didnt_use=0 → metric=1 (preferred over A)
        Entry C: outstanding=0, unremarkable=0, didnt_use=0 → metric=0 (most preferred)
        limit=2: C and B win explore; A is excluded.
        Current impl (top-2 by -confidence) picks A (confidence=0.99) and B.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Metric-2",
            outstanding_count=2,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.99,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Metric-1",
            outstanding_count=0,
            unremarkable_count=1,
            didnt_use_count=0,
            confidence=0.85,
            score=0.85,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Metric-0",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.70,
            score=0.70,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=2)

        assert "Metric-0" in result
        assert "Metric-1" in result
        assert "Metric-2" not in result


# ---------------------------------------------------------------------------
# TestFromAC_SlotDedup — AC3
# ---------------------------------------------------------------------------


class TestSlotDedup:
    """AC3: explore > challenge > regular dedup priority.

    An entry placed in explore is excluded from the challenge pool, which
    allows a *different* entry to fill the challenge slot.  Without dedup,
    the same entry would occupy both pools and the challenge slot would be
    "wasted" — resulting in fewer unique entries overall or the wrong entry
    filling the challenge slot.
    """

    @pytest.mark.asyncio
    async def test_explore_dedup_frees_challenge_slot_for_different_entry(self, tmp_path: Path) -> None:
        """Entry with lowest metric AND lowest outstanding goes to explore only.

        The challenge slot then goes to the next-best outstanding_count candidate.
        Without proper dedup, challenge would reselect the same explore entry and
        the expected challenge pick would be absent from the result.

        Setup (limit=4 → explore=2, challenge=2, regular=0):
          A: metric=0, outstanding=0 → explore #1 (also best challenge candidate)
          B: metric=1, outstanding=5 → explore #2
          C: metric=10, outstanding=0 → challenge #1 after A is deduped
          D: metric=10, outstanding=1 → challenge #2
          E: metric=10, outstanding=5, confidence=0.99 → NOT in result (no regular pool)
          F: metric=10, outstanding=5, confidence=0.98 → NOT in result

        Current impl (top-4 by -confidence): E(0.99), F(0.98), D(0.74), C(0.73) — C IS
        in result but for wrong reason; A and B are NOT in result.  Assert A in result fails.
        """
        a = _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-A",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.71,
            score=0.71,
        )
        b = _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-B",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.70,
            score=0.70,
        )
        ch1 = _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Challenge-C",
            outstanding_count=0,
            unremarkable_count=5,
            didnt_use_count=5,
            confidence=0.73,
            score=0.73,
        )
        ch2 = _write_entry(
            tmp_path,
            entry_id=_uuid(4),
            title="Challenge-D",
            outstanding_count=1,
            unremarkable_count=5,
            didnt_use_count=5,
            confidence=0.74,
            score=0.74,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(5),
            title="Excluded-E",
            outstanding_count=5,
            unremarkable_count=5,
            didnt_use_count=5,
            confidence=0.99,
            score=0.99,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(6),
            title="Excluded-F",
            outstanding_count=5,
            unremarkable_count=5,
            didnt_use_count=5,
            confidence=0.98,
            score=0.98,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=4)

        # Explore and proper dedup must produce these four
        assert a.title in result
        assert b.title in result
        assert ch1.title in result
        assert ch2.title in result
        # No regular pool → excluded
        assert "Excluded-E" not in result
        assert "Excluded-F" not in result


# ---------------------------------------------------------------------------
# TestFromAC_FinalSort — AC4
# ---------------------------------------------------------------------------


class TestFinalSort:
    """AC4: Final list sorted by (state_rank, -score, id) regardless of pool origin.

    Callers receive a single ordered list; pool membership is invisible.
    The sort key change from -confidence to -score is the key observable:
    an entry with higher score but lower confidence must appear before one
    with lower score but higher confidence.
    """

    @pytest.mark.asyncio
    async def test_higher_score_before_lower_score_within_same_state(self, tmp_path: Path) -> None:
        """Within the same state tier, higher score appears before lower score.

        Both entries are curated (same state_rank).  Score ordering must override
        confidence ordering.  Current impl sorts by -confidence; new sorts by -score.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="LowScore",
            state="curated",
            confidence=0.99,
            score=0.72,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="HighScore",
            state="curated",
            confidence=0.75,
            score=0.98,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=10)

        assert result.index("HighScore") < result.index("LowScore")

    @pytest.mark.asyncio
    async def test_sort_uses_score_not_confidence(self, tmp_path: Path) -> None:
        """The sort key is -score, not -confidence.

        Entry A: confidence=0.99, score=0.72 → should appear AFTER B
        Entry B: confidence=0.75, score=0.98 → should appear FIRST (higher score)

        Current impl puts A first (higher confidence).  New impl puts B first.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="HighConf-LowScore",
            state="curated",
            confidence=0.99,
            score=0.72,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="LowConf-HighScore",
            state="curated",
            confidence=0.75,
            score=0.98,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=10)

        assert result.index("LowConf-HighScore") < result.index("HighConf-LowScore")

    @pytest.mark.asyncio
    async def test_pool_origin_does_not_affect_position_in_final_sort(self, tmp_path: Path) -> None:
        """Explore entry with low score appears after regular entry with high score.

        The final sort is (state_rank, -score, id) — pool membership is irrelevant.
        Explore-LowScore (_uuid(1)) wins the explore slot (metric=0) but its score=0.70
        means it appears after Regular-HighScore (score=0.99, metric=50) in the output.

        Current impl: both entries confidence=0.85 → sorted by id; _uuid(1) < _uuid(2)
        so Explore-LowScore appears FIRST.  New impl: -score puts Regular-HighScore first.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-LowScore",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.85,
            score=0.70,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Regular-HighScore",
            outstanding_count=50,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.85,
            score=0.99,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=10)

        assert result.index("Regular-HighScore") < result.index("Explore-LowScore")


# ---------------------------------------------------------------------------
# TestFromAC_Tiebreak — AC5
# ---------------------------------------------------------------------------


class TestTiebreak:
    """AC5: When pool-selection metric is equal across candidates, lowest id wins.

    Tests are designed so the current confidence-based sort picks a different
    winner than the new id-based tiebreak, guaranteeing RED failure.
    """

    @pytest.mark.asyncio
    async def test_explore_tiebreak_selects_lowest_id_over_highest_confidence(self, tmp_path: Path) -> None:
        """Three entries all with metric=0; lowest two ids win explore slots.

        Entry A: id=_uuid(1), confidence=0.72 → new: explore #1 (lowest id)
        Entry B: id=_uuid(2), confidence=0.85 → new: explore #2 (second id)
        Entry C: id=_uuid(3), confidence=0.99 → current: #1 by confidence, excluded by id tiebreak

        limit=2: only 2 entries returned.
        Current impl: C(0.99), B(0.85) → A is absent.  Test asserts A in result → FAILS.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Low-ID",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.72,
            score=0.72,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Mid-ID",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.85,
            score=0.85,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="High-ID",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.99,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=2)

        assert "Low-ID" in result
        assert "Mid-ID" in result
        assert "High-ID" not in result

    @pytest.mark.asyncio
    async def test_challenge_tiebreak_selects_lowest_id_over_highest_confidence(self, tmp_path: Path) -> None:
        """Three challenge candidates with equal outstanding_count; lowest two ids win.

        Setup (limit=4 → explore=2, challenge=2, regular=0):
          Explore picks E1 and E2 (metric=0, low confidence).
          Three challenge candidates all have outstanding=2:
            CC-Low  (_uuid(3)): confidence=0.75 → challenge #1 (lowest id)
            CC-Mid  (_uuid(4)): confidence=0.87 → challenge #2 (second id)
            CC-High (_uuid(5)): confidence=0.99 → excluded (highest id)

        Current: top-4 by -confidence = CC-High(0.99), CC-Mid(0.87), E1(0.90), E2(0.89)
        → CC-High IS returned; CC-Low is NOT.  Test assertion CC-Low in result FAILS.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Explore-1",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.90,
            score=0.90,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Explore-2",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.89,
            score=0.89,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Chal-Low-ID",
            outstanding_count=2,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.75,
            score=0.75,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(4),
            title="Chal-Mid-ID",
            outstanding_count=2,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.87,
            score=0.87,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(5),
            title="Chal-High-ID",
            outstanding_count=2,
            unremarkable_count=10,
            didnt_use_count=10,
            confidence=0.99,
            score=0.99,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=4)

        assert "Chal-Low-ID" in result
        assert "Chal-Mid-ID" in result
        assert "Chal-High-ID" not in result


# ---------------------------------------------------------------------------
# TestFromAC_StateFilter — AC6
# ---------------------------------------------------------------------------


class TestStateFilter:
    """AC6: Recall includes approved/curated/contested; excludes disputed/stale/deleted/pending.

    Tests are designed as integration probes: contested must be included AND the slot
    logic must work.  The failing condition in the current impl is that the slot selection
    (explore by lowest metric) doesn't exist, so the current sort picks the high-confidence
    curated entry instead of the low-confidence contested entry that wins the explore slot.
    """

    @pytest.mark.asyncio
    async def test_contested_entry_wins_explore_slot_over_high_confidence_curated(self, tmp_path: Path) -> None:
        """Contested entry with lowest metric wins the single explore slot (limit=1).

        Entry disputed (metric=0) is excluded by state filter.
        Entry contested (metric=1) has the lowest metric among in-scope entries.
        Entry curated (metric=8, confidence=0.99) would win by -confidence but NOT by slot.

        Current impl: curated (0.99) is returned first.
        New impl: contested (lowest metric) wins the explore slot.
        """
        _write_entry(
            tmp_path,
            entry_id=_uuid(1),
            title="Disputed-Zero",
            state="disputed",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            confidence=0.99,
            score=0.99,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(2),
            title="Contested-Low",
            state="contested",
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=1,
            confidence=0.72,
            score=0.72,
        )
        _write_entry(
            tmp_path,
            entry_id=_uuid(3),
            title="Curated-HighConf",
            state="curated",
            outstanding_count=4,
            unremarkable_count=2,
            didnt_use_count=2,
            confidence=0.99,
            score=0.99,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent=_AGENT, limit=1)

        # Contested wins the explore slot (lowest metric among in-scope entries)
        assert "Contested-Low" in result
        # High-confidence curated is NOT returned (only 1 slot, filled by contested)
        assert "Curated-HighConf" not in result
        # Disputed is always excluded by state filter
        assert "Disputed-Zero" not in result
