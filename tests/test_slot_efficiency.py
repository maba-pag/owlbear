"""RED-phase tests for slot-efficiency auto-stale transition (task #1844).

P2-05: Slot-efficiency — auto-stale transition.

AC coverage:
- AC1: check_slot_efficiency(entry: MemoryEntry) -> bool in owlbear_memory.engine;
       returns True when didnt_use_count > STALE_THRESHOLD x max(outstanding_count +
       unremarkable_count, 1); exported from owlbear_memory __init__.py.
- AC2: MemoryEngine.try_stale_transition(entry: MemoryEntry) -> MemoryEntry;
       transitions {approved, curated, contested} -> stale when predicate fires;
       silent no-op for {stale, disputed, deleted, pending} or False predicate;
       no OCC; logs INFO on transition.
- AC3: Returns MemoryEntry with state=STALE + refreshed updated_at when fired;
       persists via _write_updated_entry; no disk write when no transition needed.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry
from owlbear_memory.models import MemoryState

# Guard: check_slot_efficiency does not exist yet — import will fail until implemented.
try:
    from owlbear_memory.engine import check_slot_efficiency as _check_slot_efficiency_engine

    _CSE_ENGINE = _check_slot_efficiency_engine
except ImportError:
    _CSE_ENGINE = None  # type: ignore[assignment]

try:
    from owlbear_memory import check_slot_efficiency as _check_slot_efficiency_pkg

    _CSE_PKG = _check_slot_efficiency_pkg
except ImportError:
    _CSE_PKG = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"
_TS_EARLIER = "2026-05-24T08:00:00+00:00"

_ID_A = "550e8400-e29b-41d4-a716-446655441844"
_ID_B = "550e8400-e29b-41d4-a716-446655441845"
_ID_C = "550e8400-e29b-41d4-a716-446655441846"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(  # noqa: PLR0913
    entry_id: str = _ID_A,
    state: str = "approved",
    didnt_use_count: int = 0,
    outstanding_count: int = 0,
    unremarkable_count: int = 0,
    updated_at: str = _TS,
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        title=f"Entry-{state}",
        content="Content.",
        categories=["domain-knowledge"],
        confidence=0.9,
        state=state,
        scope_agents=["test-agent"],
        source_agent="test-agent",
        created_at=_TS,
        updated_at=updated_at,
        outstanding_count=outstanding_count,
        unremarkable_count=unremarkable_count,
        didnt_use_count=didnt_use_count,
        score=0.9,
    )


def _seed_entry(  # noqa: PLR0913
    tmp_path: Path,
    entry_id: str,
    state: str,
    didnt_use_count: int = 0,
    outstanding_count: int = 0,
    unremarkable_count: int = 0,
    updated_at: str = _TS,
) -> None:
    """Write a raw markdown entry file to tmp_path with given state and counters."""
    content = (
        "---\n"
        f"id: {entry_id}\n"
        f"title: Entry-{state}\n"
        "categories:\n"
        "- domain-knowledge\n"
        "confidence: 0.9\n"
        f"state: {state}\n"
        "scope_agents:\n"
        "- test-agent\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{updated_at}'\n"
        "approved_at: null\n"
        f"outstanding_count: {outstanding_count}\n"
        f"unremarkable_count: {unremarkable_count}\n"
        f"didnt_use_count: {didnt_use_count}\n"
        "score: 0.9\n"
        "---\n\n"
        "Content.\n"
    )
    (tmp_path / f"{entry_id}.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# AC1 — check_slot_efficiency pure function
# ---------------------------------------------------------------------------


class TestSlotEfficiency:
    """AC1: check_slot_efficiency pure function and export from owlbear_memory."""

    # --- Happy path ---

    def test_returns_true_when_didnt_use_exceeds_threshold(self) -> None:
        # STALE_THRESHOLD=50; denominator=max(0+0,1)=1 → limit=50; 51 > 50 → True
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=51, outstanding_count=0, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is True

    def test_returns_false_when_didnt_use_below_threshold(self) -> None:
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=49, outstanding_count=0, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is False

    def test_returns_false_when_all_counters_zero(self) -> None:
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=0, outstanding_count=0, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is False

    # --- Boundary conditions ---

    def test_boundary_exactly_equal_to_threshold_is_false(self) -> None:
        # Strict greater-than: 50 > 50 is False
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=50, outstanding_count=0, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is False

    def test_boundary_one_above_threshold_is_true(self) -> None:
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=51, outstanding_count=0, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is True

    def test_boundary_one_below_threshold_is_false(self) -> None:
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=49, outstanding_count=0, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is False

    # --- Denominator scaling ---

    def test_denominator_scales_threshold_with_nonzero_counters(self) -> None:
        # outstanding=2, unremarkable=3 → denominator=5 → limit=250; 251 > 250 → True
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=251, outstanding_count=2, unremarkable_count=3)
        assert _CSE_ENGINE(entry) is True

    def test_denominator_scaled_boundary_exactly_equal_is_false(self) -> None:
        # outstanding=2, unremarkable=3 → denominator=5 → limit=250; 250 > 250 is False
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=250, outstanding_count=2, unremarkable_count=3)
        assert _CSE_ENGINE(entry) is False

    def test_denominator_floor_at_one_when_counters_zero(self) -> None:
        # max(0+0, 1) = 1 → must not raise; with floor=1: 0 > 50 → False
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=0, outstanding_count=0, unremarkable_count=0)
        result = _CSE_ENGINE(entry)
        assert result is False

    def test_outstanding_only_scales_denominator(self) -> None:
        # outstanding=3, unremarkable=0 → denominator=3 → limit=150; 151 → True
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=151, outstanding_count=3, unremarkable_count=0)
        assert _CSE_ENGINE(entry) is True

    def test_unremarkable_only_scales_denominator(self) -> None:
        # outstanding=0, unremarkable=4 → denominator=4 → limit=200; 201 → True
        if _CSE_ENGINE is None:
            pytest.fail("check_slot_efficiency not implemented in owlbear_memory.engine")
        entry = _make_entry(didnt_use_count=201, outstanding_count=0, unremarkable_count=4)
        assert _CSE_ENGINE(entry) is True

    # --- Export from owlbear_memory package ---

    def test_importable_from_owlbear_memory_package(self) -> None:
        if _CSE_PKG is None:
            pytest.fail("check_slot_efficiency not exported from owlbear_memory __init__.py")
        entry = _make_entry(didnt_use_count=51)
        assert _CSE_PKG(entry) is True


# ---------------------------------------------------------------------------
# AC2 + AC3 — MemoryEngine.try_stale_transition
# ---------------------------------------------------------------------------


class TestTryStaleTransition:
    """AC2+AC3: MemoryEngine.try_stale_transition() transitions and persistence."""

    # --- Eligible states: approved, curated, contested → stale ---

    def test_approved_entry_transitions_to_stale(self, tmp_path: Path) -> None:
        _seed_entry(tmp_path, _ID_A, "approved", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.STALE

    def test_curated_entry_transitions_to_stale(self, tmp_path: Path) -> None:
        _seed_entry(tmp_path, _ID_A, "curated", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.STALE

    def test_contested_entry_transitions_to_stale(self, tmp_path: Path) -> None:
        _seed_entry(tmp_path, _ID_A, "contested", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.STALE

    # --- Return value integrity ---

    def test_returned_entry_is_memory_entry_instance(self, tmp_path: Path) -> None:
        _seed_entry(tmp_path, _ID_A, "approved", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        result = engine.try_stale_transition(entry)
        assert isinstance(result, MemoryEntry)

    def test_returned_entry_has_refreshed_updated_at(self, tmp_path: Path) -> None:
        _seed_entry(tmp_path, _ID_A, "approved", didnt_use_count=51, updated_at=_TS_EARLIER)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        result = engine.try_stale_transition(entry)
        assert result.updated_at != _TS_EARLIER

    def test_predicate_false_returns_entry_with_unchanged_state(self, tmp_path: Path) -> None:
        # didnt_use_count=0 → predicate False → no transition
        entry = _make_entry(state="approved", didnt_use_count=0)
        engine = MemoryEngine(tmp_path)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.APPROVED

    # --- Persistence: disk write on transition ---

    def test_transition_is_persisted_to_disk(self, tmp_path: Path) -> None:
        _seed_entry(tmp_path, _ID_A, "approved", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        engine.try_stale_transition(entry)
        # Re-read from disk with a fresh engine to confirm persistence
        reloaded = MemoryEngine(tmp_path)
        entries = reloaded.load()
        matching = [e for e in entries if e.id == _ID_A]
        assert len(matching) == 1
        assert matching[0].state == MemoryState.STALE

    def test_no_disk_write_when_predicate_false(self, tmp_path: Path) -> None:
        # No entries seeded; predicate False (didnt_use=0) → no file should be created
        entry = _make_entry(state="approved", didnt_use_count=0)
        engine = MemoryEngine(tmp_path)
        before_files = set(tmp_path.glob("*.md"))
        engine.try_stale_transition(entry)
        after_files = set(tmp_path.glob("*.md"))
        assert before_files == after_files

    def test_no_disk_write_for_ineligible_state(self, tmp_path: Path) -> None:
        # State=pending is ineligible even with high didnt_use_count
        entry = _make_entry(state="pending", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        before_files = set(tmp_path.glob("*.md"))
        engine.try_stale_transition(entry)
        after_files = set(tmp_path.glob("*.md"))
        assert before_files == after_files

    # --- Ineligible states: silent no-op, no error ---

    def test_stale_state_returns_entry_without_error(self, tmp_path: Path) -> None:
        entry = _make_entry(state="stale", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.STALE

    def test_disputed_state_returns_entry_without_error(self, tmp_path: Path) -> None:
        entry = _make_entry(state="disputed", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.DISPUTED

    def test_deleted_state_returns_entry_without_error(self, tmp_path: Path) -> None:
        entry = _make_entry(state="deleted", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.DELETED

    def test_pending_state_returns_entry_without_error(self, tmp_path: Path) -> None:
        entry = _make_entry(state="pending", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        result = engine.try_stale_transition(entry)
        assert result.state == MemoryState.PENDING

    def test_no_exception_raised_for_any_ineligible_state(self, tmp_path: Path) -> None:
        engine = MemoryEngine(tmp_path)
        for state in ("stale", "disputed", "deleted", "pending"):
            entry = _make_entry(state=state, didnt_use_count=51)
            engine.try_stale_transition(entry)  # must not raise

    def test_ineligible_state_entry_updated_at_not_refreshed(self, tmp_path: Path) -> None:
        entry = _make_entry(state="disputed", didnt_use_count=51, updated_at=_TS_EARLIER)
        engine = MemoryEngine(tmp_path)
        result = engine.try_stale_transition(entry)
        assert result.updated_at == _TS_EARLIER

    # --- Logging ---

    def test_logs_info_on_transition(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        _seed_entry(tmp_path, _ID_A, "approved", didnt_use_count=51)
        engine = MemoryEngine(tmp_path)
        engine.load()
        entry = engine.get_entry(_ID_A)
        with caplog.at_level(logging.INFO, logger="owlbear_memory.engine"):
            engine.try_stale_transition(entry)
        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) >= 1

    def test_no_log_when_no_transition(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        entry = _make_entry(state="approved", didnt_use_count=0)
        engine = MemoryEngine(tmp_path)
        with caplog.at_level(logging.INFO, logger="owlbear_memory.engine"):
            engine.try_stale_transition(entry)
        assert len(caplog.records) == 0
