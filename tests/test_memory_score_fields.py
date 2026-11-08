"""Memory assessment counter and score computation regression tests.

Behavioral coverage:
- AC1: MemoryEntry has outstanding_count, unremarkable_count, didnt_use_count (int = 0),
    score (float = 0.0) in owlbear_memory;
       defaults enable backward-compatible deserialization of pre-existing entries;
       the outstanding boost and unremarkable penalty come from the owner's settings, not from code.
- AC2: compute_score(confidence, outstanding_count, unremarkable_count, points) -> float returns
       confidence + (outstanding_count * boost) - (unremarkable_count * penalty);
       exported from owlbear_memory.
- AC3: MemoryEngine.save() initializes score=confidence, counters=0;
    storage round-trip (write+read) preserves counter and score values in owlbear_memory.
"""

# ruff: noqa: PLC0415

from __future__ import annotations

from pathlib import Path

import pytest
from owlbear_memory import Points

POINTS = Points(outstanding_boost=0.1, unremarkable_penalty=0.01)

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


class TestModelFields:
    """AC1: MemoryEntry assessment counter/score fields and named constants."""

    # --- MemoryEntry field defaults ---

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

    # --- The points come from the owner's settings, never from code ---

    def test_points_ship_no_default_values(self) -> None:
        """Points has no defaults: a caller that holds no setting cannot rank or score by a value from code."""
        from owlbear_memory import Points

        with pytest.raises(TypeError):
            Points()  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            Points(outstanding_boost=0.1)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# AC2 — compute_score function
# ---------------------------------------------------------------------------


class TestComputeScore:
    """AC2: compute_score formula and export from owlbear_memory."""

    def test_compute_score_basic_formula(self) -> None:
        """compute_score returns confidence + outstanding*boost - unremarkable*penalty."""
        from owlbear_memory import compute_score

        # 0.8 + (2 * 0.1) - (3 * 0.01) = 0.8 + 0.2 - 0.03 = 0.97
        result = compute_score(confidence=0.8, outstanding_count=2, unremarkable_count=3, points=POINTS)
        assert result == pytest.approx(0.97)

    def test_compute_score_zero_counters_returns_confidence(self) -> None:
        """compute_score with all-zero counters returns confidence unchanged."""
        from owlbear_memory import compute_score

        result = compute_score(confidence=0.9, outstanding_count=0, unremarkable_count=0, points=POINTS)
        assert result == pytest.approx(0.9)

    def test_compute_score_outstanding_only(self) -> None:
        """compute_score accumulates outstanding boosts: confidence + N*boost."""
        from owlbear_memory import compute_score

        # 0.7 + (1 * 0.1) = 0.8
        result = compute_score(confidence=0.7, outstanding_count=1, unremarkable_count=0, points=POINTS)
        assert result == pytest.approx(0.8)

    def test_compute_score_unremarkable_only(self) -> None:
        """compute_score deducts unremarkable penalties: confidence - N*penalty."""
        from owlbear_memory import compute_score

        # 0.9 - (5 * 0.01) = 0.9 - 0.05 = 0.85
        result = compute_score(confidence=0.9, outstanding_count=0, unremarkable_count=5, points=POINTS)
        assert result == pytest.approx(0.85)

    def test_compute_score_return_type_is_float(self) -> None:
        """compute_score always returns float."""
        from owlbear_memory import compute_score

        result = compute_score(confidence=0.8, outstanding_count=0, unremarkable_count=0, points=POINTS)
        assert isinstance(result, float)

    def test_each_point_value_moves_the_score_on_its_own(self) -> None:
        """Changing only the boost, or only the penalty, changes only its own term of the score."""
        from owlbear_memory import Points, compute_score

        base = compute_score(0.8, 4, 7, Points(0.1, 0.01))
        assert compute_score(0.8, 4, 7, Points(0.2, 0.01)) == pytest.approx(base + 4 * 0.1)
        assert compute_score(0.8, 4, 7, Points(0.1, 0.02)) == pytest.approx(base - 7 * 0.01)


# ---------------------------------------------------------------------------
# AC3 — MemoryEngine.save() initialization and storage round-trips
# ---------------------------------------------------------------------------


class TestSaveAndRoundTrip:
    """AC3: MemoryEngine.save() initializes score/counters; round-trips preserve them in both packages."""

    # --- MemoryEngine.save() (owlbear_memory) ---

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
