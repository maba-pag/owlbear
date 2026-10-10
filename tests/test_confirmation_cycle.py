"""Protect the memory confirmation cycle and its optimistic concurrency ordering."""

from __future__ import annotations

from pathlib import Path

import pytest
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage
from owlbear_memory.errors import ConcurrencyError, TransitionError, ValidationError
from owlbear_memory.models import ChallengeRecord

# Mined from #1845: factually-wrong confirmation, disputed transitions, and OCC ordering.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"
_TS_WRONG = "2025-01-01T00:00:00+00:00"
_TS_APPROVED = "2026-05-20T08:00:00+00:00"  # non-null approved_at for downgrade-contract tests

_ID_APPROVED = "550e8400-e29b-41d4-a716-446655451001"
_ID_CURATED = "550e8400-e29b-41d4-a716-446655451002"
_ID_CONTESTED = "550e8400-e29b-41d4-a716-446655451003"
_ID_PENDING = "550e8400-e29b-41d4-a716-446655451004"
_ID_DISPUTED = "550e8400-e29b-41d4-a716-446655451005"
_ID_STALE = "550e8400-e29b-41d4-a716-446655451006"
_ID_DELETED = "550e8400-e29b-41d4-a716-446655451007"

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
    """Create a MemoryEntry without challenge records."""
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
    challenge_task_id: str | None = None,
) -> MemoryEntry:
    """Create a MemoryEntry with an optional existing challenge."""
    entry = _make_entry_base(entry_id, state, updated_at=updated_at, approved_at=approved_at)
    if challenge_task_id is None:
        return entry
    challenge = ChallengeRecord(
        task_id=challenge_task_id,
        revision=entry.revision,
        recorded_at=updated_at,
    )
    return entry.model_copy(update={"challenges": [challenge]})


def _write_entry(directory: Path, entry: MemoryEntry) -> Path:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return path


def _write_legacy_entry(directory: Path, task_id: str | None) -> Path:
    path = directory / f"{_ID_CONTESTED}.md"
    legacy_task = "null" if task_id is None else task_id
    path.write_text(
        "---\n"
        f"id: {_ID_CONTESTED}\n"
        "title: Test Entry\n"
        "categories:\n"
        "- domain-knowledge\n"
        "confidence: 0.9\n"
        "state: contested\n"
        "scope_agents:\n"
        "- test-agent\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{_TS}'\n"
        "approved_at: null\n"
        f"contested_by_task: {legacy_task}\n"
        "---\n\nSome content\n",
        encoding="utf-8",
    )
    return path


def _engine_with_entries(directory: Path, *entries: MemoryEntry) -> MemoryEngine:
    for entry in entries:
        _write_entry(directory, entry)
    return MemoryEngine(memory_dir=directory)


def _record_factually_wrong(engine: MemoryEngine, entry_id: str, task_id: str) -> MemoryEntry:
    entry = engine.get_entry(entry_id)
    result = engine.record_factually_wrong(
        entry_id,
        task_id=task_id,
        expected_revision=entry.revision,
    )
    return result.entry


# ---------------------------------------------------------------------------
# TestFromAC_ConfirmationCycle — AC1, AC2, AC3, AC4
# ---------------------------------------------------------------------------


class TestConfirmationCycle:
    """Confirmation cycle: record_factually_wrong() transitions and field contract."""

    def test_legacy_challenge_migrates_with_entry_revision_and_timestamp(self, tmp_path: Path) -> None:
        path = _write_legacy_entry(tmp_path, _TASK_A)
        engine = MemoryEngine(memory_dir=tmp_path)
        migrated = engine.get_entry(_ID_CONTESTED)

        assert len(migrated.challenges) == 1
        assert migrated.challenges[0].task_id == _TASK_A
        assert migrated.challenges[0].revision == migrated.revision
        assert migrated.challenges[0].recorded_at == migrated.updated_at == _TS
        assert "contested_by_task" not in MemoryEntry.model_fields

        updated = engine.edit(_ID_CONTESTED, {"title": "Updated"}, expected_revision=migrated.revision)
        reloaded = MemoryEngine(memory_dir=tmp_path).get_entry(_ID_CONTESTED)
        serialized = path.read_text(encoding="utf-8")

        assert updated.revision != migrated.revision
        assert reloaded.challenges == migrated.challenges
        assert "challenges:" in serialized
        assert "contested_by_task" not in serialized

    @pytest.mark.parametrize("legacy_task_id", ["task 1", "tâche-1", "t" * 200])
    def test_legacy_challenge_keeps_previously_accepted_task_id(self, tmp_path: Path, legacy_task_id: str) -> None:
        path = _write_legacy_entry(tmp_path, legacy_task_id)
        engine = MemoryEngine(memory_dir=tmp_path)
        migrated = engine.get_entry(_ID_CONTESTED)

        assert [challenge.task_id for challenge in migrated.challenges] == [legacy_task_id]

        engine.edit(_ID_CONTESTED, {"title": "Updated"}, expected_revision=migrated.revision)
        reloaded = MemoryEngine(memory_dir=tmp_path).get_entry(_ID_CONTESTED)

        assert [challenge.task_id for challenge in reloaded.challenges] == [legacy_task_id]
        assert "contested_by_task" not in path.read_text(encoding="utf-8")

    def test_legacy_null_challenge_migrates_to_empty_list_and_is_removed_on_write(self, tmp_path: Path) -> None:
        path = _write_legacy_entry(tmp_path, None)
        engine = MemoryEngine(memory_dir=tmp_path)
        migrated = engine.get_entry(_ID_CONTESTED)

        assert migrated.challenges == []

        updated = engine.edit(_ID_CONTESTED, {"title": "Updated"}, expected_revision=migrated.revision)
        serialized = path.read_text(encoding="utf-8")

        assert updated.challenges == []
        assert "challenges:" in serialized
        assert "contested_by_task" not in serialized

    # ------------------------------------------------------------------
    # AC1 — challenge field and storage contract
    # ------------------------------------------------------------------

    def test_memory_entry_has_empty_challenges_by_default(self) -> None:
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        assert entry.challenges == []
        assert "contested_by_task" not in MemoryEntry.model_fields

    def test_challenges_survive_storage_roundtrip(self, tmp_path: Path) -> None:
        entry = _make_entry(_ID_APPROVED, MemoryState.APPROVED, challenge_task_id=_TASK_A)
        path = _write_entry(tmp_path, entry)
        serialized = path.read_text(encoding="utf-8")
        reloaded = storage.read_entry(path)

        assert reloaded is not None
        assert reloaded.challenges == entry.challenges
        assert "challenges:" in serialized
        assert "contested_by_task" not in serialized

    # ------------------------------------------------------------------
    # AC1 — approved and curated transitions to contested
    # ------------------------------------------------------------------

    def test_approved_entry_transitions_to_contested(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong on approved entry → contested state."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        assert result.state == MemoryState.CONTESTED

    def test_curated_entry_transitions_to_contested(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong on curated entry → contested state."""
        entry = _make_entry_base(_ID_CURATED, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_CURATED, _TASK_A)
        assert result.state == MemoryState.CONTESTED

    def test_challenge_stored_on_initial_call(self, tmp_path: Path) -> None:
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        assert len(result.challenges) == 1
        assert result.challenges[0].task_id == _TASK_A
        assert result.challenges[0].revision == entry.revision
        assert result.challenges[0].recorded_at == result.updated_at

    def test_contested_entry_remains_in_recall_results(self, tmp_path: Path) -> None:
        """AC1: contested entry is still returned by get_entries (not excluded from recall)."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        entries = engine.get_entries()
        assert any(e.id == _ID_APPROVED for e in entries)

    def test_approved_entry_clears_approved_at_on_contested_transition(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong on approved entry clears approved_at to None (downgrade contract).

        Fixture has non-null approved_at so the clearing assertion cannot false-green.
        """
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        assert result.approved_at is None

    def test_approved_at_cleared_persisted_after_contested_transition(self, tmp_path: Path) -> None:
        """AC1: approved_at=None clearing is persisted to storage on approved→contested transition."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        reloaded = engine.get_entry(_ID_APPROVED)
        assert reloaded.approved_at is None

    def test_empty_task_id_raises_validation_error(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong with empty task_id raises ValidationError."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ValidationError):
            engine.record_factually_wrong(_ID_APPROVED, task_id="", expected_revision=entry.revision)

    def test_whitespace_task_id_raises_validation_error(self, tmp_path: Path) -> None:
        """AC1: record_factually_wrong with whitespace-only task_id raises ValidationError."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ValidationError):
            engine.record_factually_wrong(_ID_APPROVED, task_id="   ", expected_revision=entry.revision)

    # ------------------------------------------------------------------
    # AC2 — second confirmation: different task → disputed; None → initial
    # ------------------------------------------------------------------

    def test_different_task_appends_second_challenge_and_transitions_to_disputed(self, tmp_path: Path) -> None:
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED, challenge_task_id=_TASK_A)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_CONTESTED, _TASK_B)

        assert result.state == MemoryState.DISPUTED
        assert [challenge.task_id for challenge in result.challenges] == [_TASK_A, _TASK_B]
        assert all(challenge.revision == entry.revision for challenge in result.challenges)
        assert result.challenges[1].recorded_at == result.updated_at
        assert MemoryEngine(memory_dir=tmp_path).get_entry(_ID_CONTESTED).challenges == result.challenges

    def test_contested_with_no_challenges_stays_contested_and_records_first(self, tmp_path: Path) -> None:
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_CONTESTED, _TASK_B)

        assert result.state == MemoryState.CONTESTED
        assert [challenge.task_id for challenge in result.challenges] == [_TASK_B]
        assert result.challenges[0].revision == entry.revision

    # ------------------------------------------------------------------
    # AC3 — same-task no-op + non-voteable state guard
    # ------------------------------------------------------------------

    def test_same_task_id_on_contested_returns_entry_unchanged(self, tmp_path: Path) -> None:
        """A replay returns the stored result without rewriting the receipt or entry."""
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED)
        engine = _engine_with_entries(tmp_path, entry)
        first = _record_factually_wrong(engine, _ID_CONTESTED, _TASK_A)
        path = tmp_path / f"{_ID_CONTESTED}.md"
        before_replay = path.read_bytes()

        replay = engine.record_factually_wrong(
            _ID_CONTESTED,
            task_id=_TASK_A,
            expected_revision=entry.revision,
        )

        assert replay.already_applied is True
        assert replay.entry.state == MemoryState.CONTESTED
        assert [challenge.task_id for challenge in replay.entry.challenges] == [_TASK_A]
        assert replay.entry.updated_at == first.updated_at
        assert path.read_bytes() == before_replay

    def test_challenge_without_receipt_is_deduplicated_before_state_guard(self, tmp_path: Path) -> None:
        entry = _make_entry(_ID_CONTESTED, MemoryState.CONTESTED, challenge_task_id=_TASK_A)
        engine = _engine_with_entries(tmp_path, entry)
        path = tmp_path / f"{_ID_CONTESTED}.md"
        before_replay = path.read_bytes()

        replay = engine.record_factually_wrong(
            _ID_CONTESTED,
            task_id=_TASK_A,
            expected_revision=entry.revision,
        )

        assert replay.already_applied is True
        assert replay.recorded_bucket == "factually_wrong"
        assert path.read_bytes() == before_replay

    def test_second_task_replay_after_dispute_is_already_applied(self, tmp_path: Path) -> None:
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        contested = engine.get_entry(_ID_APPROVED)

        first = engine.record_factually_wrong(
            _ID_APPROVED,
            task_id=_TASK_B,
            expected_revision=contested.revision,
        )
        path = tmp_path / f"{_ID_APPROVED}.md"
        before_replay = path.read_bytes()
        replay = engine.record_factually_wrong(
            _ID_APPROVED,
            task_id=_TASK_B,
            expected_revision=contested.revision,
        )

        assert first.entry.state == MemoryState.DISPUTED
        assert replay.already_applied is True
        assert replay.entry.challenges == first.entry.challenges
        assert path.read_bytes() == before_replay

    def test_pending_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: pending is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_PENDING, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            _record_factually_wrong(engine, _ID_PENDING, _TASK_A)

    def test_disputed_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: disputed is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_DISPUTED, MemoryState.DISPUTED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            _record_factually_wrong(engine, _ID_DISPUTED, _TASK_A)

    def test_stale_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: stale is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_STALE, MemoryState.STALE)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            _record_factually_wrong(engine, _ID_STALE, _TASK_A)

    def test_deleted_state_raises_transition_error(self, tmp_path: Path) -> None:
        """AC3: deleted is not voteable → TransitionError."""
        entry = _make_entry_base(_ID_DELETED, MemoryState.DELETED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(TransitionError):
            _record_factually_wrong(engine, _ID_DELETED, _TASK_A)

    # ------------------------------------------------------------------
    # AC4 — OCC guard
    # ------------------------------------------------------------------

    def test_occ_mismatch_raises_concurrency_error(self, tmp_path: Path) -> None:
        """A stale content revision raises ConcurrencyError."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A, expected_revision="0" * 16)

    def test_occ_mismatch_does_not_mutate_entry(self, tmp_path: Path) -> None:
        """AC4: ConcurrencyError is raised without mutating the entry."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(_ID_APPROVED, task_id=_TASK_A, expected_revision="0" * 16)
        after = engine.get_entry(_ID_APPROVED)
        assert after.state == MemoryState.APPROVED

    def test_occ_match_allows_transition(self, tmp_path: Path) -> None:
        """AC4: matching expected_updated_at proceeds to state transition."""
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED, updated_at=_TS)
        engine = _engine_with_entries(tmp_path, entry)
        result = _record_factually_wrong(engine, _ID_APPROVED, _TASK_A)
        assert result.state == MemoryState.CONTESTED

    def test_occ_evaluated_before_state_guard(self, tmp_path: Path) -> None:
        """AC4 + AC3: OCC guard runs before state guard — ConcurrencyError beats TransitionError."""
        # pending is non-voteable; a stale revision must fail before the state guard.
        entry = _make_entry_base(_ID_PENDING, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(_ID_PENDING, task_id=_TASK_A, expected_revision="0" * 16)

    def test_occ_mismatch_beats_empty_task_id_validation(self, tmp_path: Path) -> None:
        """AC3+AC4: OCC guard evaluated before task_id validation —
        ConcurrencyError beats ValidationError (empty task_id).
        """
        # Combines OCC mismatch with invalid task_id=""; OCC must be checked first per AC3 ordering clause.
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(_ID_APPROVED, task_id="", expected_revision="0" * 16)

    def test_occ_mismatch_beats_whitespace_task_id_validation(self, tmp_path: Path) -> None:
        """AC3+AC4: OCC guard evaluated before task_id validation —
        ConcurrencyError beats ValidationError (whitespace task_id).
        """
        entry = _make_entry_base(_ID_APPROVED, MemoryState.APPROVED)
        engine = _engine_with_entries(tmp_path, entry)
        with pytest.raises(ConcurrencyError):
            engine.record_factually_wrong(_ID_APPROVED, task_id="   ", expected_revision="0" * 16)
