"""RED-phase tests for confirmation cycle: factually-wrong → contested/disputed.

Task #1845 — P2-06: Confirmation cycle — factually-wrong to contested/disputed

AC coverage:
- AC1: MemoryEntry.contested_by_task field in both packages (default None, frontmatter-serialized);
       record_factually_wrong raises ValidationError for empty/whitespace task_id;
       approved/curated entries transition to contested with contested_by_task = task_id;
       contested entry remains in recall results.
- AC2: contested + non-None contested_by_task ≠ task_id → disputed;
       contested + contested_by_task=None → initial confirmation (stays contested, stores task_id).
- AC3: same task_id on contested → no mutation, entry returned unchanged;
       non-voteable states raise TransitionError.
- AC4: expected_updated_at mismatch raises ConcurrencyError (before state logic);
       None skips OCC check unconditionally.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState
from owlbear_memory import storage
from owlbear_memory.errors import ConcurrencyError, TransitionError, ValidationError
from owlbear_mcp_memory.models import MemoryEntry as McpMemoryEntry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"
_TS_WRONG = "2025-01-01T00:00:00+00:00"
_TS_APPROVED = "2026-05-20T08:00:00+00:00"  # non-null approved_at for downgrade-contract tests

_ID_APPROVED  = "550e8400-e29b-41d4-a716-446655451001"
_ID_CURATED   = "550e8400-e29b-41d4-a716-446655451002"
_ID_CONTESTED = "550e8400-e29b-41d4-a716-446655451003"
_ID_PENDING   = "550e8400-e29b-41d4-a716-446655451004"
_ID_DISPUTED  = "550e8400-e29b-41d4-a716-446655451005"
_ID_STALE     = "550e8400-e29b-41d4-a716-446655451006"
_ID_DELETED   = "550e8400-e29b-41d4-a716-446655451007"

_TASK_A = "task-123"
_TASK_B = "task-456"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry_base(
    entry_id: str,
    state: MemoryState,
    updated_at: str = _TS,
    approved_at: str | None = None,
) -> MemoryEntry:
    """Create a MemoryEntry without contested_by_task (uses only pre-existing fields)."""
    return MemoryEntry(
        id=entry_id,
        title="Test Entry",
        content="Some content",
        categories=["domain-knowledge"],
        confidence=0.9,
        state=state,
        scope_agents=["test-agent"],
        source_agent="test-agent",
        created_at=_TS,
        updated_at=updated_at,
        approved_at=approved_at,
    )


def _make_entry(
    entry_id: str,
    state: MemoryState,
    updated_at: str = _TS,
    approved_at: str | None = None,
    contested_by_task: str | None = None,
) -> MemoryEntry:
    """Create a MemoryEntry WITH contested_by_task field (fails in RED when field is missing)."""
    return MemoryEntry(
        id=entry_id,
        title="Test Entry",
        content="Some content",
        categories=["domain-knowledge"],
        confidence=0.9,
        state=state,
        scope_agents=["test-agent"],
        source_agent="test-agent",
        created_at=_TS,
        updated_at=updated_at,
        approved_at=approved_at,
        contested_by_task=contested_by_task,
    )


def _write_entry(directory: Path, entry: MemoryEntry) -> Path:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return path


def _engine_with_entries(directory: Path, *entries: MemoryEntry) -> MemoryEngine:
    for entry in entries:
        _write_entry(directory, entry)
    return MemoryEngine(memory_dir=directory)


# ---------------------------------------------------------------------------
# TestFromAC_ConfirmationCycle — AC1, AC2, AC3, AC4
# ---------------------------------------------------------------------------


class TestFromAC_ConfirmationCycle:
    """Confirmation cycle: record_factually_wrong() transitions and field contract."""

    # ------------------------------------------------------------------
    # AC1 — contested_by_task field existence in both packages
    # ------------------------------------------------------------------

    def test_owlbear_memory_entry_has_contested_by_task_default_none(self) -> None:
        """AC1: MemoryEntry in owlbear_memory has contested_by_task with default None."""
        entry = MemoryEntry(
            id=_ID_APPROVED,
            title="Test",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            state=MemoryState.APPROVED,
            scope_agents=["a"],
            source_agent="agent",
            created_at=_TS,
            updated_at=_TS,
        )
        assert entry.contested_by_task is None

    def test_owlbear_mcp_memory_entry_has_contested_by_task_default_none(self) -> None:
        """AC1: MemoryEntry in owlbear_mcp_memory has contested_by_task with default None."""
        entry = McpMemoryEntry(
            id=_ID_APPROVED,
            title="Test",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            state="approved",
            scope_agents=["a"],
            source_agent="agent",
            created_at=_TS,
            updated_at=_TS,
        )
        assert entry.contested_by_task is None

    def test_contested_by_task_survives_storage_roundtrip_owlbear_memory(self, tmp_path: Path) -> None:
        """AC1: contested_by_task is frontmatter-serialized and survives write/read roundtrip."""
        entry = _make_entry(_ID_APPROVED, MemoryState.APPROVED, contested_by_task=_TASK_A)
        path = _write_entry(tmp_path, entry)
        reloaded = storage.read_entry(path)
        assert reloaded is not None
        assert reloaded.contested_by_task == _TASK_A

    def test_contested_by_task_survives_storage_roundtrip_owlbear_mcp_memory(
        self, tmp_path: Path
    ) -> None:
        """AC1: contested_by_task is frontmatter-serialized in owlbear_mcp_memory engine roundtrip."""
        from owlbear_mcp_memory.engine import MemoryEngine as McpEngine

        entry = McpMemoryEntry(
            id=_ID_APPROVED,
            title="Test",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            state="approved",
            scope_agents=["a"],
            source_agent="agent",
            created_at=_TS,
            updated_at=_TS,
            contested_by_task=_TASK_A,
        )
        engine = McpEngine(memory_dir=tmp_path)
        engine.write(entry)
        reloaded = engine.get_entry(_ID_APPROVED)
        assert reloaded.contested_by_task == _TASK_A

    # ------------------------------------------------------------------
    # AC1 — approved and curated transitions to contested
    # ------------------------------------------------------------------

    def test_approved_entry_transitions_to_contested(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong on approved entry → contested state."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A)
        assert result.state == MemoryState.CONTESTED

    def test_curated_entry_transitions_to_contested(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong on curated entry → contested state."""
        entry = _make_entry_base(_ID_CURATED, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_CURATED, task_id=_TASK_A)
        assert result.state == MemoryState.CONTESTED

    def test_contested_by_task_stored_on_initial_call(self, tmp_path: Path) -> None:
        """AC1: contested_by_task is set to task_id on initial transition to contested."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A)
        assert result.contested_by_task == _TASK_A

    def test_contested_entry_remains_in_recall_results(self, tmp_path: Path) -> None:
        """AC1: contested entry is still returned by get_entries (not excluded from recall)."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A)
        entries = engine.get_entries()
        assert any(e.id == _ID_APPROVED for e in entries)

    def test_approved_entry_clears_approved_at_on_contested_transition(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong on approved entry clears approved_at to None (downgrade contract).

        Fixture has non-null approved_at so the clearing assertion cannot false-green.
        """
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A)
        assert result.approved_at is None

    def test_approved_at_cleared_persisted_after_contested_transition(self, tmp_path: Path) -> None:
        """AC1: approved_at=None clearing is persisted to storage on approved→contested transition."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A)
        reloaded = engine.get_entry(_ID_APPROVED)
        assert reloaded.approved_at is None

    def test_empty_task_id_raises_validation_error(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong with empty task_id raises ValidationError."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ValidationError):
            engine.record_factually_wrong(_ID_APPROVED, task_id="")

    def test_whitespace_task_id_raises_validation_error(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong with whitespace-only task_id raises ValidationError."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ValidationError):
            engine.record_factually_wrong(_ID_APPROVED, task_id="   ")

    # ------------------------------------------------------------------
    # AC2 — second confirmation: different task → disputed; None → initial
    # ------------------------------------------------------------------

    def test_different_task_id_on_contested_transitions_to_disputed(self, tmp_path: Path) -> None:
        """AC2: contested entry with non-None contested_by_task ≠ task_id → disputed."""
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED, contested_by_task=_TASK_A)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_CONTESTED, task_id=_TASK_B)
        assert result.state == MemoryState.DISPUTED

    def test_contested_with_none_contested_by_task_treated_as_initial_confirmation(
        self, tmp_path: Path
    ) -> None:
        """AC2 edge: contested with contested_by_task=None → stays contested, stores task_id."""
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED, contested_by_task=None)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_CONTESTED, task_id=_TASK_B)
        assert result.state == MemoryState.CONTESTED
        assert result.contested_by_task == _TASK_B

    # ------------------------------------------------------------------
    # AC3 — same-task no-op + non-voteable state guard
    # ------------------------------------------------------------------

    def test_same_task_id_on_contested_returns_entry_unchanged(self, tmp_path: Path) -> None:
        """AC3: same task_id on contested entry → no mutation, original entry returned."""
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED, contested_by_task=_TASK_A)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_CONTESTED, task_id=_TASK_A)
        assert result.state == MemoryState.CONTESTED
        assert result.contested_by_task == _TASK_A
        assert result.updated_at == _TS  # no mutation means updated_at is unchanged

    def test_pending_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: pending is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_PENDING, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            engine.record_factually_wrong(_ID_PENDING, task_id=_TASK_A)

    def test_disputed_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: disputed is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_DISPUTED, MemoryState.DISPUTED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            engine.record_factually_wrong(_ID_DISPUTED, task_id=_TASK_A)

    def test_stale_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: stale is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_STALE, MemoryState.STALE)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            engine.record_factually_wrong(_ID_STALE, task_id=_TASK_A)

    def test_deleted_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: deleted is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_DELETED, MemoryState.DELETED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            engine.record_factually_wrong(_ID_DELETED, task_id=_TASK_A)

    # ------------------------------------------------------------------
    # AC4 — OCC guard
    # ------------------------------------------------------------------

    def test_occ_mismatch_raises_concurrency_error(self, tmp_path: Path) -> None:
        """AC4: expected_updated_at mismatch raises ConcurrencyError."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(
                _ID_APPROVED, task_id=_TASK_A, expected_updated_at=_TS_WRONG
            )

    def test_occ_mismatch_does_not_mutate_entry(self, tmp_path: Path) -> None:
        """AC4: ConcurrencyError is raised without mutating the entry."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(
                _ID_APPROVED, task_id=_TASK_A, expected_updated_at=_TS_WRONG
            )
        after = engine.get_entry(_ID_APPROVED)
        assert after.state == MemoryState.APPROVED

    def test_occ_none_skips_check_and_proceeds(self, tmp_path: Path) -> None:
        """AC4: expected_updated_at=None skips OCC check (unconditional write)."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A, expected_updated_at=None)
        assert result.state == MemoryState.CONTESTED

    def test_occ_match_allows_transition(self, tmp_path: Path) -> None:
        """AC4: matching expected_updated_at proceeds to state transition."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED, updated_at=_TS)
        engine = _engine_with_entries(tmp_path, entry)
        result = engine.record_factually_wrong(
            _ID_APPROVED, task_id=_TASK_A, expected_updated_at=_TS
        )
        assert result.state == MemoryState.CONTESTED

    def test_occ_evaluated_before_state_guard(self, tmp_path: Path) -> None:
        """AC4 + AC3: OCC guard runs before state guard — ConcurrencyError beats TransitionError."""
        # pending is non-voteable; wrong expected_updated_at → ConcurrencyError, not TransitionError
        entry = _make_entry_base(_ID_PENDING, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(
                _ID_PENDING, task_id=_TASK_A, expected_updated_at=_TS_WRONG
            )

    def test_occ_mismatch_beats_empty_task_id_validation(self, tmp_path: Path) -> None:
        """AC3+AC4: OCC guard evaluated before task_id validation — ConcurrencyError beats ValidationError (empty task_id)."""
        # Combines OCC mismatch with invalid task_id=""; OCC must be checked first per AC3 ordering clause.
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(
                _ID_APPROVED, task_id="", expected_updated_at=_TS_WRONG
            )

    def test_occ_mismatch_beats_whitespace_task_id_validation(self, tmp_path: Path) -> None:
        """AC3+AC4: OCC guard evaluated before task_id validation — ConcurrencyError beats ValidationError (whitespace task_id)."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(
                _ID_APPROVED, task_id="   ", expected_updated_at=_TS_WRONG
            )
