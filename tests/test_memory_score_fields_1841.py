"""RED-phase tests for memory assessment counters and score computation (task #1841).

P2-02: Model fields — assessment counters and score computation.

AC coverage:
- AC1: MemoryEntry has outstanding_count, unremarkable_count, didnt_use_count (int = 0),
       score (float = 0.0) in both owlbear_memory and owlbear_mcp_memory;
       defaults enable backward-compatible deserialization of pre-existing entries;
       OUTSTANDING_BOOST=0.1, UNREMARKABLE_PENALTY=0.01, STALE_THRESHOLD=50 in engine module.
- AC2: compute_score(confidence, outstanding_count, unremarkable_count) -> float returns
       confidence + (outstanding_count * OUTSTANDING_BOOST) - (unremarkable_count * UNREMARKABLE_PENALTY);
       exported from owlbear_memory.
- AC3: MemoryEngine.save() initializes score=confidence, counters=0;
       storage round-trip (write+read) preserves counter and score values in both packages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

_TS = "2026-01-01T00:00:00+00:00"

_ID_A = "550e8400-e29b-41d4-a716-446655441841"
_ID_B = "550e8400-e29b-41d4-a716-446655441842"
_ID_C = "550e8400-e29b-41d4-a716-446655441843"


def _min_entry_data(**overrides: object) -> dict:
    """Return minimum required fields for MemoryEntry construction (no new AC1 fields)."""
    base: dict = {
        "id": _ID_A,
        "title": "Test entry",
        "content": "Test content",
        "categories": ["process"],
        "confidence": 0.8,
        "source_agent": "test-agent",
        "created_at": _TS,
        "updated_at": _TS,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# AC1 — Model fields and named constants
# ---------------------------------------------------------------------------


class TestFromAC_ModelFields:
    """AC1: MemoryEntry assessment counter/score fields and named constants."""

    # --- owlbear_memory: new field defaults ---

    def test_outstanding_count_default_owlbear_memory(self) -> None:
        """MemoryEntry.outstanding_count defaults to 0 in owlbear_memory."""
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.outstanding_count == 0

    def test_unremarkable_count_default_owlbear_memory(self) -> None:
        """MemoryEntry.unremarkable_count defaults to 0 in owlbear_memory."""
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.unremarkable_count == 0

    def test_didnt_use_count_default_owlbear_memory(self) -> None:
        """MemoryEntry.didnt_use_count defaults to 0 in owlbear_memory."""
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.didnt_use_count == 0

    def test_score_default_owlbear_memory(self) -> None:
        """MemoryEntry.score defaults to 0.0 in owlbear_memory."""
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.score == 0.0

    # --- owlbear_mcp_memory: new field defaults ---

    def test_outstanding_count_default_owlbear_mcp_memory(self) -> None:
        """MemoryEntry.outstanding_count defaults to 0 in owlbear_mcp_memory."""
        from owlbear_mcp_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.outstanding_count == 0

    def test_unremarkable_count_default_owlbear_mcp_memory(self) -> None:
        """MemoryEntry.unremarkable_count defaults to 0 in owlbear_mcp_memory."""
        from owlbear_mcp_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.unremarkable_count == 0

    def test_didnt_use_count_default_owlbear_mcp_memory(self) -> None:
        """MemoryEntry.didnt_use_count defaults to 0 in owlbear_mcp_memory."""
        from owlbear_mcp_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.didnt_use_count == 0

    def test_score_default_owlbear_mcp_memory(self) -> None:
        """MemoryEntry.score defaults to 0.0 in owlbear_mcp_memory."""
        from owlbear_mcp_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data())
        assert entry.score == 0.0

    # --- Backward-compatible deserialization ---

    def test_backward_compat_no_new_fields_owlbear_memory(self) -> None:
        """Pre-existing entry dict (missing new fields) deserializes with defaults in owlbear_memory."""
        from owlbear_memory.models import MemoryEntry

        data = _min_entry_data()  # no outstanding_count, unremarkable_count, didnt_use_count, score
        entry = MemoryEntry(**data)
        assert entry.outstanding_count == 0
        assert entry.unremarkable_count == 0
        assert entry.didnt_use_count == 0
        assert entry.score == 0.0

    def test_backward_compat_no_new_fields_owlbear_mcp_memory(self) -> None:
        """Pre-existing entry dict (missing new fields) deserializes with defaults in owlbear_mcp_memory."""
        from owlbear_mcp_memory.models import MemoryEntry

        data = _min_entry_data()  # no outstanding_count, unremarkable_count, didnt_use_count, score
        entry = MemoryEntry(**data)
        assert entry.outstanding_count == 0
        assert entry.unremarkable_count == 0
        assert entry.didnt_use_count == 0
        assert entry.score == 0.0

    # --- Named constants in engine module ---

    def test_outstanding_boost_constant_value(self) -> None:
        """OUTSTANDING_BOOST = 0.1 is defined in owlbear_memory engine module."""
        from owlbear_memory import engine

        assert engine.OUTSTANDING_BOOST == 0.1

    def test_unremarkable_penalty_constant_value(self) -> None:
        """UNREMARKABLE_PENALTY = 0.01 is defined in owlbear_memory engine module."""
        from owlbear_memory import engine

        assert engine.UNREMARKABLE_PENALTY == 0.01

    def test_stale_threshold_constant_value(self) -> None:
        """STALE_THRESHOLD = 50 is defined in owlbear_memory engine module."""
        from owlbear_memory import engine

        assert engine.STALE_THRESHOLD == 50

    def test_outstanding_boost_is_float(self) -> None:
        """OUTSTANDING_BOOST is a float."""
        from owlbear_memory import engine

        assert isinstance(engine.OUTSTANDING_BOOST, float)

    def test_unremarkable_penalty_is_float(self) -> None:
        """UNREMARKABLE_PENALTY is a float."""
        from owlbear_memory import engine

        assert isinstance(engine.UNREMARKABLE_PENALTY, float)

    def test_stale_threshold_is_int(self) -> None:
        """STALE_THRESHOLD is an int."""
        from owlbear_memory import engine

        assert isinstance(engine.STALE_THRESHOLD, int)


# ---------------------------------------------------------------------------
# AC2 — compute_score function
# ---------------------------------------------------------------------------


class TestFromAC_ComputeScore:
    """AC2: compute_score formula and export from owlbear_memory."""

    def test_compute_score_importable_from_owlbear_memory(self) -> None:
        """compute_score is importable from owlbear_memory and callable."""
        from owlbear_memory import compute_score

        assert callable(compute_score)

    def test_compute_score_basic_formula(self) -> None:
        """compute_score returns confidence + outstanding*BOOST - unremarkable*PENALTY."""
        from owlbear_memory import compute_score

        # 0.8 + (2 * 0.1) - (3 * 0.01) = 0.8 + 0.2 - 0.03 = 0.97
        result = compute_score(confidence=0.8, outstanding_count=2, unremarkable_count=3)
        assert result == pytest.approx(0.97)

    def test_compute_score_zero_counters_returns_confidence(self) -> None:
        """compute_score with all-zero counters returns confidence unchanged."""
        from owlbear_memory import compute_score

        result = compute_score(confidence=0.9, outstanding_count=0, unremarkable_count=0)
        assert result == pytest.approx(0.9)

    def test_compute_score_outstanding_only(self) -> None:
        """compute_score accumulates outstanding boosts: confidence + N*OUTSTANDING_BOOST."""
        from owlbear_memory import compute_score

        # 0.7 + (1 * 0.1) = 0.8
        result = compute_score(confidence=0.7, outstanding_count=1, unremarkable_count=0)
        assert result == pytest.approx(0.8)

    def test_compute_score_unremarkable_only(self) -> None:
        """compute_score deducts unremarkable penalties: confidence - N*UNREMARKABLE_PENALTY."""
        from owlbear_memory import compute_score

        # 0.9 - (5 * 0.01) = 0.9 - 0.05 = 0.85
        result = compute_score(confidence=0.9, outstanding_count=0, unremarkable_count=5)
        assert result == pytest.approx(0.85)

    def test_compute_score_at_stale_threshold_boundary(self) -> None:
        """compute_score with unremarkable_count == STALE_THRESHOLD."""
        from owlbear_memory import compute_score, engine

        # STALE_THRESHOLD=50: 0.7 + 0 - (50 * 0.01) = 0.7 - 0.5 = 0.2
        result = compute_score(
            confidence=0.7,
            outstanding_count=0,
            unremarkable_count=engine.STALE_THRESHOLD,
        )
        assert result == pytest.approx(0.2)

    def test_compute_score_return_type_is_float(self) -> None:
        """compute_score always returns float."""
        from owlbear_memory import compute_score

        result = compute_score(confidence=0.8, outstanding_count=0, unremarkable_count=0)
        assert isinstance(result, float)

    def test_compute_score_formula_matches_engine_constants(self) -> None:
        """compute_score result is consistent with OUTSTANDING_BOOST and UNREMARKABLE_PENALTY constants."""
        from owlbear_memory import compute_score, engine

        confidence = 0.8
        outstanding = 4
        unremarkable = 7
        expected = confidence + (outstanding * engine.OUTSTANDING_BOOST) - (unremarkable * engine.UNREMARKABLE_PENALTY)
        assert compute_score(
            confidence=confidence,
            outstanding_count=outstanding,
            unremarkable_count=unremarkable,
        ) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# AC3 — MemoryEngine.save() initialization and storage round-trips
# ---------------------------------------------------------------------------


class TestFromAC_SaveAndRoundTrip:
    """AC3: MemoryEngine.save() initializes score/counters; round-trips preserve them in both packages."""

    # --- MemoryEngine.save() (owlbear_memory) ---

    def test_save_initializes_score_to_confidence(self, tmp_path: Path) -> None:
        """MemoryEngine.save() sets score = confidence for new entries."""
        from owlbear_memory import MemoryCategory, MemoryEngine

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = eng.save(
            title="Score init test",
            content="Entry content",
            categories=[MemoryCategory.PROCESS],
            confidence=0.85,
            source_agent="test-agent",
            scope_agents=[],
        )
        assert entry.score == pytest.approx(0.85)

    def test_save_initializes_outstanding_count_to_zero(self, tmp_path: Path) -> None:
        """MemoryEngine.save() sets outstanding_count = 0 for new entries."""
        from owlbear_memory import MemoryCategory, MemoryEngine

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = eng.save(
            title="Counter init test",
            content="Entry content",
            categories=[MemoryCategory.DOMAIN_KNOWLEDGE],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )
        assert entry.outstanding_count == 0

    def test_save_initializes_unremarkable_count_to_zero(self, tmp_path: Path) -> None:
        """MemoryEngine.save() sets unremarkable_count = 0 for new entries."""
        from owlbear_memory import MemoryCategory, MemoryEngine

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = eng.save(
            title="Counter init test",
            content="Entry content",
            categories=[MemoryCategory.PITFALL],
            confidence=0.75,
            source_agent="test-agent",
            scope_agents=[],
        )
        assert entry.unremarkable_count == 0

    def test_save_initializes_didnt_use_count_to_zero(self, tmp_path: Path) -> None:
        """MemoryEngine.save() sets didnt_use_count = 0 for new entries."""
        from owlbear_memory import MemoryCategory, MemoryEngine

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = eng.save(
            title="Counter init test",
            content="Entry content",
            categories=[MemoryCategory.BEHAVIOUR],
            confidence=0.8,
            source_agent="test-agent",
            scope_agents=[],
        )
        assert entry.didnt_use_count == 0

    def test_save_score_equals_confidence_varied(self, tmp_path: Path) -> None:
        """MemoryEngine.save() score = confidence holds for multiple confidence values."""
        from owlbear_memory import MemoryCategory, MemoryEngine

        eng = MemoryEngine(memory_dir=tmp_path)
        for conf in (0.7, 0.85, 1.0):
            entry = eng.save(
                title=f"Test conf={conf}",
                content="Content",
                categories=[MemoryCategory.PROCESS],
                confidence=conf,
                source_agent="test-agent",
                scope_agents=[],
            )
            assert entry.score == pytest.approx(conf), f"score mismatch for confidence={conf}"

    # --- owlbear_memory round-trips ---

    def test_round_trip_preserves_score_owlbear_memory(self, tmp_path: Path) -> None:
        """write_entry+read_entry preserves non-default score in owlbear_memory."""
        from owlbear_memory import storage
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data(id=_ID_A, score=0.93))
        path = tmp_path / f"{_ID_A}.md"
        storage.write_entry(path, entry, memory_dir=tmp_path)
        loaded = storage.read_entry(path)
        assert loaded is not None
        assert loaded.score == pytest.approx(0.93)

    def test_round_trip_preserves_outstanding_count_owlbear_memory(self, tmp_path: Path) -> None:
        """write_entry+read_entry preserves outstanding_count in owlbear_memory."""
        from owlbear_memory import storage
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data(id=_ID_B, outstanding_count=7))
        path = tmp_path / f"{_ID_B}.md"
        storage.write_entry(path, entry, memory_dir=tmp_path)
        loaded = storage.read_entry(path)
        assert loaded is not None
        assert loaded.outstanding_count == 7

    def test_round_trip_preserves_unremarkable_count_owlbear_memory(self, tmp_path: Path) -> None:
        """write_entry+read_entry preserves unremarkable_count in owlbear_memory."""
        from owlbear_memory import storage
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data(id=_ID_C, unremarkable_count=12))
        path = tmp_path / f"{_ID_C}.md"
        storage.write_entry(path, entry, memory_dir=tmp_path)
        loaded = storage.read_entry(path)
        assert loaded is not None
        assert loaded.unremarkable_count == 12

    def test_round_trip_preserves_didnt_use_count_owlbear_memory(self, tmp_path: Path) -> None:
        """write_entry+read_entry preserves didnt_use_count in owlbear_memory."""
        from owlbear_memory import storage
        from owlbear_memory.models import MemoryEntry

        entry = MemoryEntry(**_min_entry_data(id=_ID_A, didnt_use_count=3))
        path = tmp_path / f"{_ID_A}.md"
        storage.write_entry(path, entry, memory_dir=tmp_path)
        loaded = storage.read_entry(path)
        assert loaded is not None
        assert loaded.didnt_use_count == 3

    # --- owlbear_mcp_memory round-trips ---

    def test_round_trip_preserves_score_owlbear_mcp_memory(self, tmp_path: Path) -> None:
        """write+load preserves non-default score in owlbear_mcp_memory."""
        from owlbear_mcp_memory.engine import MemoryEngine
        from owlbear_mcp_memory.models import MemoryEntry

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = MemoryEntry(**_min_entry_data(id=_ID_A, score=0.91))
        eng.write(entry)
        entries = eng.load()
        match = next((e for e in entries if e.id == _ID_A), None)
        assert match is not None
        assert match.score == pytest.approx(0.91)

    def test_round_trip_preserves_outstanding_count_owlbear_mcp_memory(self, tmp_path: Path) -> None:
        """write+load preserves outstanding_count in owlbear_mcp_memory."""
        from owlbear_mcp_memory.engine import MemoryEngine
        from owlbear_mcp_memory.models import MemoryEntry

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = MemoryEntry(**_min_entry_data(id=_ID_B, outstanding_count=5))
        eng.write(entry)
        entries = eng.load()
        match = next((e for e in entries if e.id == _ID_B), None)
        assert match is not None
        assert match.outstanding_count == 5

    def test_round_trip_preserves_unremarkable_count_owlbear_mcp_memory(self, tmp_path: Path) -> None:
        """write+load preserves unremarkable_count in owlbear_mcp_memory."""
        from owlbear_mcp_memory.engine import MemoryEngine
        from owlbear_mcp_memory.models import MemoryEntry

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = MemoryEntry(**_min_entry_data(id=_ID_C, unremarkable_count=8))
        eng.write(entry)
        entries = eng.load()
        match = next((e for e in entries if e.id == _ID_C), None)
        assert match is not None
        assert match.unremarkable_count == 8

    def test_round_trip_preserves_didnt_use_count_owlbear_mcp_memory(self, tmp_path: Path) -> None:
        """write+load preserves didnt_use_count in owlbear_mcp_memory."""
        from owlbear_mcp_memory.engine import MemoryEngine
        from owlbear_mcp_memory.models import MemoryEntry

        eng = MemoryEngine(memory_dir=tmp_path)
        entry = MemoryEntry(**_min_entry_data(id=_ID_A, didnt_use_count=4))
        eng.write(entry)
        entries = eng.load()
        match = next((e for e in entries if e.id == _ID_A), None)
        assert match is not None
        assert match.didnt_use_count == 4
