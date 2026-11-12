"""Current-points scoring and backward-compatible rating fields."""

from __future__ import annotations

from pathlib import Path

import pytest
from owlbear_memory import MemoryEngine, MemoryEntry, Points, compute_score, entry_score

_TS = "2026-01-01T00:00:00+00:00"


def _min_entry_data(**overrides: object) -> dict:
    return {
        "id": "550e8400-e29b-41d4-a716-446655441841",
        "title": "Test entry",
        "content": "Test content",
        "categories": ["process"],
        "confidence": 0.8,
        "source_agent": "test-agent",
        "created_at": _TS,
        "updated_at": _TS,
        **overrides,
    }


def test_backward_compat_no_new_fields_owlbear_memory() -> None:
    entry = MemoryEntry(**_min_entry_data())
    assert (entry.outstanding_count, entry.unremarkable_count, entry.didnt_use_count, entry.score) == (0, 0, 0, 0.0)


def test_points_ship_no_default_values() -> None:
    with pytest.raises(TypeError):
        Points()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Points(outstanding_boost=0.1)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("confidence", "outstanding", "unremarkable", "points", "expected"),
    [
        (0.8, 2, 3, Points(0.1, 0.01), 0.97),
        (0.9, 0, 0, Points(0.1, 0.01), 0.9),
        (0.8, 0, 0, Points(0.1, 0.01), 0.8),
        (0.8, 4, 7, Points(0.1, 0.01), 1.13),
        (0.8, 4, 7, Points(0.2, 0.01), 1.53),
        (0.8, 4, 7, Points(0.1, 0.02), 1.06),
        (0.8, 2, 2, Points(0.1, 0.01), 0.98),
        (0.8, 2, 2, Points(0.3, 0.05), 1.3),
    ],
)
def test_current_points_score_contract(
    confidence: float, outstanding: int, unremarkable: int, points: Points, expected: float
) -> None:
    entry = MemoryEntry(
        **_min_entry_data(
            confidence=confidence, outstanding_count=outstanding, unremarkable_count=unremarkable, score=9.0
        )
    )
    computed = compute_score(confidence, outstanding, unremarkable, points)
    assert isinstance(computed, float)
    assert computed == pytest.approx(expected)
    assert entry_score(entry, points) == pytest.approx(expected)


def test_save_score_equals_confidence_varied(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path)
    for confidence in (0.7, 0.85, 1.0):
        entry = engine.save(
            title=f"Test conf={confidence}",
            content="Content",
            categories=["process"],
            confidence=confidence,
            source_agent="test-agent",
            scope_agents=[],
        )
        assert entry.score == pytest.approx(confidence)
        assert (entry.outstanding_count, entry.unremarkable_count, entry.didnt_use_count) == (0, 0, 0)
