"""RED-phase tests for MemoryEngine and MtimeScanCache (task #1668).

AC coverage:
- AC1: approve() — curated→approved transition, approved_at and updated_at set;
       TransitionError for pending/approved/deleted source states
- AC2: edit() — pending+scope_agents→curated, approved→curated (clears approved_at),
       curated stays curated, pending-no-scope_agents stays pending; TransitionError on deleted
- AC3: delete() — hard-delete for pending (file gone), soft-delete for curated/approved
       (state=deleted, updated_at updated); TransitionError when already deleted
- AC4: OCC via expected_updated_at (string comparison) on approve/edit/delete;
       save() has no expected_updated_at parameter
- AC5: MtimeScanCache.has_changed() — True on first call, False on unchanged mtime,
       True when mtime_ns changes; get_entries() skips reparse when False
- AC6: save() — pending state, UUIDv4 id, ISO 8601 timestamps, writes to disk, returns MemoryEntry
- AC7: get_entries() — skips unparseable files (parse_errors incremented),
       duplicate UUID → keep later updated_at, log warning
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_memory.engine import MemoryEngine, MtimeScanCache
from owlbear_memory.errors import ConcurrencyError, NotFoundError, TransitionError
from owlbear_memory.models import MemoryEntry, MemoryState
from owlbear_memory import storage

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

_CURATED_ID = "550e8400-e29b-41d4-a716-446655440001"
_PENDING_ID = "550e8400-e29b-41d4-a716-446655440002"
_APPROVED_ID = "550e8400-e29b-41d4-a716-446655440003"
_DELETED_ID = "550e8400-e29b-41d4-a716-446655440004"
_DEDUP_ID = "550e8400-e29b-41d4-a716-446655440005"

_TS_EARLY = "2026-01-01T00:00:00+00:00"
_TS_LATE = "2026-06-01T12:00:00+00:00"
_TS_WRONG = "2026-01-01T00:00:00+00:00"
_TS_APPROVED = "2026-03-01T00:00:00+00:00"


def _make_entry(
    entry_id: str,
    state: MemoryState,
    updated_at: str = _TS_EARLY,
    approved_at: str | None = None,
    scope_agents: list[str] | None = None,
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        title="Test Entry",
        content="Some content",
        categories=["domain-knowledge"],
        confidence=0.9,
        state=state,
        scope_agents=scope_agents if scope_agents is not None else [],
        source_agent="test-agent",
        created_at=_TS_EARLY,
        updated_at=updated_at,
        approved_at=approved_at,
    )


def _write_entry(directory: Path, entry: MemoryEntry) -> Path:
    """Write a MemoryEntry file using the storage primitive."""
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)
    return path


def _engine_with_entries(directory: Path, *entries: MemoryEntry) -> MemoryEngine:
    """Create an engine backed by directory, prepopulate with entries."""
    for entry in entries:
        _write_entry(directory, entry)
    return MemoryEngine(memory_dir=directory)


# ---------------------------------------------------------------------------
# TestFromAC_Approve — AC1
# ---------------------------------------------------------------------------


class TestFromAC_Approve:
    """AC1: approve() transitions curated→approved; TransitionError on others."""

    def test_approve_curated_to_approved_returns_approved_state(self, tmp_path: Path) -> None:
        """Happy: curated entry transitions to approved state."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.approve(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.state == MemoryState.APPROVED

    def test_approve_sets_approved_at_timestamp(self, tmp_path: Path) -> None:
        """Happy: approved_at is populated after approve()."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.approve(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.approved_at is not None

    def test_approve_updates_updated_at(self, tmp_path: Path) -> None:
        """Happy: updated_at is refreshed after approve()."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.approve(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.updated_at != _TS_EARLY

    def test_approve_persists_to_disk(self, tmp_path: Path) -> None:
        """Happy: approve() writes updated entry to disk."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        engine.approve(_CURATED_ID, expected_updated_at=_TS_EARLY)

        # Reload independently and confirm state persisted
        engine2 = MemoryEngine(memory_dir=tmp_path)
        reloaded = engine2.get_entry(_CURATED_ID)
        assert reloaded.state == MemoryState.APPROVED

    def test_approve_pending_raises_transition_error(self, tmp_path: Path) -> None:
        """Error: pending→approved is not a valid transition."""
        entry = _make_entry(_PENDING_ID, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(TransitionError):
            engine.approve(_PENDING_ID, expected_updated_at=_TS_EARLY)

    def test_approve_already_approved_raises_transition_error(self, tmp_path: Path) -> None:
        """Error: approved→approved is not a valid transition."""
        entry = _make_entry(_APPROVED_ID, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(TransitionError):
            engine.approve(_APPROVED_ID, expected_updated_at=_TS_EARLY)

    def test_approve_deleted_raises_transition_error(self, tmp_path: Path) -> None:
        """Error: deleted→approved is not a valid transition."""
        entry = _make_entry(_DELETED_ID, MemoryState.DELETED)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(TransitionError):
            engine.approve(_DELETED_ID, expected_updated_at=_TS_EARLY)

    def test_approve_nonexistent_id_raises_not_found_error(self, tmp_path: Path) -> None:
        """Error: approving unknown ID raises NotFoundError."""
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(NotFoundError):
            engine.approve("550e8400-e29b-41d4-a716-999999999999", expected_updated_at=_TS_EARLY)


# ---------------------------------------------------------------------------
# TestFromAC_Edit — AC2
# ---------------------------------------------------------------------------


class TestFromAC_Edit:
    """AC2: edit() state transitions and field-update behaviour."""

    def test_edit_pending_with_scope_agents_transitions_to_curated(self, tmp_path: Path) -> None:
        """Happy: pending + scope_agents in fields → curated."""
        entry = _make_entry(_PENDING_ID, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _PENDING_ID,
            fields={"scope_agents": ["builder"]},
            expected_updated_at=_TS_EARLY,
        )

        assert result.state == MemoryState.CURATED

    def test_edit_approved_to_curated_clears_approved_at(self, tmp_path: Path) -> None:
        """Happy: approved→curated clears approved_at."""
        entry = _make_entry(_APPROVED_ID, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _APPROVED_ID,
            fields={"title": "Updated Title"},
            expected_updated_at=_TS_EARLY,
        )

        assert result.state == MemoryState.CURATED
        assert result.approved_at is None

    def test_edit_approved_updates_updated_at(self, tmp_path: Path) -> None:
        """Happy: edit on approved entry updates updated_at."""
        entry = _make_entry(_APPROVED_ID, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _APPROVED_ID,
            fields={"title": "New Title"},
            expected_updated_at=_TS_EARLY,
        )

        assert result.updated_at != _TS_EARLY

    def test_edit_curated_stays_curated(self, tmp_path: Path) -> None:
        """Happy: editing curated entry without scope change stays curated."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _CURATED_ID,
            fields={"title": "Updated Title"},
            expected_updated_at=_TS_EARLY,
        )

        assert result.state == MemoryState.CURATED

    def test_edit_curated_stays_curated_updates_field(self, tmp_path: Path) -> None:
        """Edge: field update is applied even when state is unchanged."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _CURATED_ID,
            fields={"title": "Patched Title"},
            expected_updated_at=_TS_EARLY,
        )

        assert result.title == "Patched Title"

    def test_edit_pending_without_scope_agents_stays_pending(self, tmp_path: Path) -> None:
        """Happy: pending entry without scope_agents in fields stays pending."""
        entry = _make_entry(_PENDING_ID, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _PENDING_ID,
            fields={"title": "Changed Title"},
            expected_updated_at=_TS_EARLY,
        )

        assert result.state == MemoryState.PENDING

    def test_edit_pending_without_scope_agents_updates_field(self, tmp_path: Path) -> None:
        """Edge: field update applied on pending entry even without scope change."""
        entry = _make_entry(_PENDING_ID, MemoryState.PENDING)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(
            _PENDING_ID,
            fields={"title": "New Pending Title"},
            expected_updated_at=_TS_EARLY,
        )

        assert result.title == "New Pending Title"

    def test_edit_deleted_raises_transition_error(self, tmp_path: Path) -> None:
        """Error: editing a deleted entry raises TransitionError."""
        entry = _make_entry(_DELETED_ID, MemoryState.DELETED)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(TransitionError):
            engine.edit(
                _DELETED_ID,
                fields={"title": "Attempt"},
                expected_updated_at=_TS_EARLY,
            )

    def test_edit_nonexistent_id_raises_not_found_error(self, tmp_path: Path) -> None:
        """Error: editing unknown ID raises NotFoundError."""
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(NotFoundError):
            engine.edit(
                "550e8400-e29b-41d4-a716-999999999999",
                fields={"title": "Ghost"},
                expected_updated_at=_TS_EARLY,
            )

    def test_edit_persists_field_change_to_disk(self, tmp_path: Path) -> None:
        """Happy: field update is written to disk."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        engine.edit(_CURATED_ID, fields={"title": "Disk Write Check"}, expected_updated_at=_TS_EARLY)

        engine2 = MemoryEngine(memory_dir=tmp_path)
        reloaded = engine2.get_entry(_CURATED_ID)
        assert reloaded.title == "Disk Write Check"


# ---------------------------------------------------------------------------
# TestFromAC_Delete — AC3
# ---------------------------------------------------------------------------


class TestFromAC_Delete:
    """AC3: delete() hard-deletes pending, soft-deletes curated/approved."""

    def test_delete_pending_removes_file_from_disk(self, tmp_path: Path) -> None:
        """Happy: deleting a pending entry removes the markdown file."""
        entry = _make_entry(_PENDING_ID, MemoryState.PENDING)
        file_path = _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.delete(_PENDING_ID, expected_updated_at=_TS_EARLY)

        assert not file_path.exists()

    def test_delete_pending_not_in_get_entries_after_hard_delete(self, tmp_path: Path) -> None:
        """Happy: hard-deleted pending entry is gone from get_entries()."""
        entry = _make_entry(_PENDING_ID, MemoryState.PENDING)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.delete(_PENDING_ID, expected_updated_at=_TS_EARLY)

        ids = [e.id for e in engine.get_entries()]
        assert _PENDING_ID not in ids

    def test_delete_curated_soft_deletes_state(self, tmp_path: Path) -> None:
        """Happy: soft-deleting curated entry sets state to deleted."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.delete(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.state == MemoryState.DELETED

    def test_delete_curated_file_still_exists(self, tmp_path: Path) -> None:
        """Edge: soft-delete keeps file on disk."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        file_path = _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.delete(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert file_path.exists()

    def test_delete_approved_soft_deletes_state(self, tmp_path: Path) -> None:
        """Happy: soft-deleting approved entry sets state to deleted."""
        entry = _make_entry(_APPROVED_ID, MemoryState.APPROVED, approved_at=_TS_APPROVED)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.delete(_APPROVED_ID, expected_updated_at=_TS_EARLY)

        assert result.state == MemoryState.DELETED

    def test_delete_curated_updates_updated_at(self, tmp_path: Path) -> None:
        """Happy: soft-delete updates the updated_at timestamp."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.delete(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.updated_at != _TS_EARLY

    def test_delete_already_deleted_raises_transition_error(self, tmp_path: Path) -> None:
        """Error: deleting already-deleted entry raises TransitionError."""
        entry = _make_entry(_DELETED_ID, MemoryState.DELETED)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(TransitionError):
            engine.delete(_DELETED_ID, expected_updated_at=_TS_EARLY)

    def test_delete_nonexistent_id_raises_not_found_error(self, tmp_path: Path) -> None:
        """Error: deleting unknown ID raises NotFoundError."""
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(NotFoundError):
            engine.delete("550e8400-e29b-41d4-a716-999999999999", expected_updated_at=_TS_EARLY)

    def test_delete_soft_persists_to_disk(self, tmp_path: Path) -> None:
        """Happy: soft-delete state is written to disk."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.delete(_CURATED_ID, expected_updated_at=_TS_EARLY)

        engine2 = MemoryEngine(memory_dir=tmp_path)
        reloaded = engine2.get_entry(_CURATED_ID)
        assert reloaded.state == MemoryState.DELETED


# ---------------------------------------------------------------------------
# TestFromAC_OCC — AC4
# ---------------------------------------------------------------------------


class TestFromAC_OCC:
    """AC4: expected_updated_at OCC on approve/edit/delete; save() has none."""

    def test_approve_wrong_expected_updated_at_raises_concurrency_error(self, tmp_path: Path) -> None:
        """Error: approve() raises ConcurrencyError on timestamp mismatch."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(ConcurrencyError):
            engine.approve(_CURATED_ID, expected_updated_at=_TS_LATE)

    def test_edit_wrong_expected_updated_at_raises_concurrency_error(self, tmp_path: Path) -> None:
        """Error: edit() raises ConcurrencyError on timestamp mismatch."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(ConcurrencyError):
            engine.edit(_CURATED_ID, fields={"title": "x"}, expected_updated_at=_TS_LATE)

    def test_delete_wrong_expected_updated_at_raises_concurrency_error(self, tmp_path: Path) -> None:
        """Error: delete() raises ConcurrencyError on timestamp mismatch."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(ConcurrencyError):
            engine.delete(_CURATED_ID, expected_updated_at=_TS_LATE)

    def test_occ_check_is_string_comparison(self, tmp_path: Path) -> None:
        """Boundary: OCC is string comparison — same datetime in different timezone format fails."""
        # _TS_EARLY is "2026-01-01T00:00:00+00:00"
        # An equivalent timestamp in Z notation should not be treated as equal (string compare)
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        with pytest.raises(ConcurrencyError):
            # "2026-01-01T00:00:00Z" is the same instant but different string
            engine.approve(_CURATED_ID, expected_updated_at="2026-01-01T00:00:00Z")

    def test_approve_correct_expected_updated_at_succeeds(self, tmp_path: Path) -> None:
        """Happy: approve() succeeds when expected_updated_at matches exactly."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.approve(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.state == MemoryState.APPROVED

    def test_edit_correct_expected_updated_at_succeeds(self, tmp_path: Path) -> None:
        """Happy: edit() succeeds when expected_updated_at matches exactly."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.edit(_CURATED_ID, fields={"title": "Updated"}, expected_updated_at=_TS_EARLY)

        assert result.title == "Updated"

    def test_delete_correct_expected_updated_at_succeeds(self, tmp_path: Path) -> None:
        """Happy: delete() succeeds when expected_updated_at matches exactly."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        engine = _engine_with_entries(tmp_path, entry)

        result = engine.delete(_CURATED_ID, expected_updated_at=_TS_EARLY)

        assert result.state == MemoryState.DELETED

    def test_save_has_no_expected_updated_at_parameter(self) -> None:
        """Boundary: save() signature does not include expected_updated_at."""
        sig = inspect.signature(MemoryEngine.save)
        assert "expected_updated_at" not in sig.parameters


# ---------------------------------------------------------------------------
# TestFromAC_MtimeScanCache — AC5
# ---------------------------------------------------------------------------


class TestFromAC_MtimeScanCache:
    """AC5: MtimeScanCache.has_changed() semantics."""

    def test_has_changed_returns_true_on_first_call(self, tmp_path: Path) -> None:
        """Happy: first call always returns True (triggers initial load)."""
        cache = MtimeScanCache(tmp_path)

        assert cache.has_changed() is True

    def test_has_changed_returns_false_on_second_call_same_mtime(self, tmp_path: Path) -> None:
        """Happy: second call without modification returns False."""
        cache = MtimeScanCache(tmp_path)
        cache.has_changed()  # prime cache

        assert cache.has_changed() is False

    def test_has_changed_returns_true_after_directory_modified(self, tmp_path: Path) -> None:
        """Happy: returns True after a file is added to the directory."""
        cache = MtimeScanCache(tmp_path)
        cache.has_changed()  # prime cache

        # Add a file — modifies directory mtime
        (tmp_path / "new-file.md").write_text("x")

        assert cache.has_changed() is True

    def test_has_changed_false_again_after_second_change_check(self, tmp_path: Path) -> None:
        """Edge: after detecting a change, subsequent stable call returns False."""
        cache = MtimeScanCache(tmp_path)
        cache.has_changed()  # prime
        (tmp_path / "new-file.md").write_text("x")
        cache.has_changed()  # detect change

        assert cache.has_changed() is False

    def test_get_entries_skips_reparse_when_mtime_unchanged(self, tmp_path: Path) -> None:
        """Edge: get_entries() does not re-read files when mtime is stable."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        # Trigger first load
        first = engine.get_entries()

        # Modify entry directly on disk — engine should NOT see change (mtime stable)
        # We patch storage.read_entry to detect if it's called again
        with patch("owlbear_memory.storage.read_entry") as mock_read:
            second = engine.get_entries()
            mock_read.assert_not_called()

        assert len(second) == len(first)


# ---------------------------------------------------------------------------
# TestFromAC_Save — AC6
# ---------------------------------------------------------------------------


class TestFromAC_Save:
    """AC6: save() creates new pending entry with generated id and timestamps."""

    def test_save_returns_memory_entry(self, tmp_path: Path) -> None:
        """Happy: save() returns a MemoryEntry instance."""
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="New Entry",
            content="Content here",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )

        assert isinstance(result, MemoryEntry)

    def test_save_creates_pending_state(self, tmp_path: Path) -> None:
        """Happy: saved entry is in pending state."""
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="Pending Entry",
            content="Content",
            categories=["pitfall"],
            confidence=0.85,
            source_agent="test-agent",
            scope_agents=[],
        )

        assert result.state == MemoryState.PENDING

    def test_save_generates_uuidv4_id(self, tmp_path: Path) -> None:
        """Happy: save() generates a UUIDv4-format id."""
        import re

        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="UUID Check",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )

        uuid_v4_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
        assert re.fullmatch(uuid_v4_pattern, result.id) is not None

    def test_save_creates_iso8601_created_at(self, tmp_path: Path) -> None:
        """Happy: created_at is a valid ISO 8601 timestamp."""
        from datetime import datetime

        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="Timestamp Check",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )

        parsed = datetime.fromisoformat(result.created_at)
        assert parsed.tzinfo is not None

    def test_save_created_at_equals_updated_at_on_creation(self, tmp_path: Path) -> None:
        """Happy: created_at equals updated_at for a newly saved entry."""
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="New",
            content="x",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )

        assert result.created_at == result.updated_at

    def test_save_writes_file_to_disk(self, tmp_path: Path) -> None:
        """Happy: save() writes at least one .md file to memory_dir."""
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="Disk Write Test",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )

        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) == 1
        assert result.id in md_files[0].read_text()

    def test_save_appears_in_get_entries(self, tmp_path: Path) -> None:
        """Happy: saved entry is retrievable via get_entries()."""
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="Visible Entry",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )

        ids = [e.id for e in engine.get_entries()]
        assert result.id in ids

    def test_save_two_calls_produce_unique_ids(self, tmp_path: Path) -> None:
        """Edge: two sequential save() calls produce different UUIDs."""
        engine = MemoryEngine(memory_dir=tmp_path)

        r1 = engine.save(
            title="A",
            content="x",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="agent",
            scope_agents=[],
        )
        r2 = engine.save(
            title="B",
            content="y",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="agent",
            scope_agents=[],
        )

        assert r1.id != r2.id

    def test_save_with_scope_agents_stores_them(self, tmp_path: Path) -> None:
        """Edge: scope_agents list is persisted in the saved entry."""
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.save(
            title="Scoped Entry",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=["builder", "reviewer"],
        )

        assert result.scope_agents == ["builder", "reviewer"]

    def test_save_timestamps_fall_within_wall_clock_bound(self, tmp_path: Path) -> None:
        """Boundary: created_at and updated_at are within before/after UTC wall-clock bound."""
        engine = MemoryEngine(memory_dir=tmp_path)

        before = datetime.now(UTC)
        result = engine.save(
            title="Wall-clock Bound",
            content="Content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        )
        after = datetime.now(UTC)

        parsed_created_at = datetime.fromisoformat(result.created_at)
        parsed_updated_at = datetime.fromisoformat(result.updated_at)

        assert before <= parsed_created_at <= after
        assert before <= parsed_updated_at <= after


# ---------------------------------------------------------------------------
# TestFromAC_LenientRead — AC7
# ---------------------------------------------------------------------------


class TestFromAC_LenientRead:
    """AC7: get_entries() lenient read and duplicate UUID deduplication."""

    def test_parse_errors_starts_at_zero(self, tmp_path: Path) -> None:
        """Boundary: engine.parse_errors is 0 before any load."""
        engine = MemoryEngine(memory_dir=tmp_path)

        assert engine.parse_errors == 0

    def test_unparseable_file_is_skipped(self, tmp_path: Path) -> None:
        """Happy: malformed markdown file is silently skipped."""
        (tmp_path / "bad-file.md").write_text("not valid frontmatter at all")
        engine = MemoryEngine(memory_dir=tmp_path)

        entries = engine.get_entries()

        assert len(entries) == 0

    def test_unparseable_file_increments_parse_errors(self, tmp_path: Path) -> None:
        """Happy: each unparseable file increments parse_errors."""
        (tmp_path / "bad1.md").write_text("garbage")
        (tmp_path / "bad2.md").write_text("also garbage")
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.get_entries()

        assert engine.parse_errors == 2

    def test_valid_file_does_not_increment_parse_errors(self, tmp_path: Path) -> None:
        """Edge: valid file leaves parse_errors unchanged."""
        entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        _write_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        engine.get_entries()

        assert engine.parse_errors == 0

    def test_duplicate_uuid_keeps_later_updated_at(self, tmp_path: Path) -> None:
        """Happy: when two files share a UUID, the one with later updated_at wins."""
        early_entry = _make_entry(_DEDUP_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        late_entry = _make_entry(_DEDUP_ID, MemoryState.CURATED, updated_at=_TS_LATE)

        # Write to different filenames to avoid overwrite
        storage.write_entry(tmp_path / "early.md", early_entry, memory_dir=tmp_path)
        storage.write_entry(tmp_path / "late.md", late_entry, memory_dir=tmp_path)

        engine = MemoryEngine(memory_dir=tmp_path)
        entries = engine.get_entries()

        # Only one entry for the duplicated UUID
        matching = [e for e in entries if e.id == _DEDUP_ID]
        assert len(matching) == 1
        assert matching[0].updated_at == _TS_LATE

    def test_duplicate_uuid_keeps_later_updated_at_with_timezone_offsets(self, tmp_path: Path) -> None:
        """Edge: dedup compares timestamps chronologically, not lexically, across offsets."""
        # Chronology in UTC:
        # - +01:00 timestamp => 2026-01-01T00:30:00+00:00 (earlier)
        # - +00:00 timestamp => 2026-01-01T00:45:00+00:00 (later)
        earlier_lexically_larger = "2026-01-01T01:30:00+01:00"
        later_lexically_smaller = "2026-01-01T00:45:00+00:00"

        first = _make_entry(_DEDUP_ID, MemoryState.CURATED, updated_at=earlier_lexically_larger)
        second = _make_entry(_DEDUP_ID, MemoryState.CURATED, updated_at=later_lexically_smaller)

        storage.write_entry(tmp_path / "first.md", first, memory_dir=tmp_path)
        storage.write_entry(tmp_path / "second.md", second, memory_dir=tmp_path)

        engine = MemoryEngine(memory_dir=tmp_path)
        entries = engine.get_entries()

        matching = [entry for entry in entries if entry.id == _DEDUP_ID]
        assert len(matching) == 1
        assert matching[0].updated_at == later_lexically_smaller

    def test_duplicate_uuid_logs_warning(self, tmp_path: Path) -> None:
        """Happy: duplicate UUID discovery emits a warning log."""
        early_entry = _make_entry(_DEDUP_ID, MemoryState.CURATED, updated_at=_TS_EARLY)
        late_entry = _make_entry(_DEDUP_ID, MemoryState.CURATED, updated_at=_TS_LATE)

        storage.write_entry(tmp_path / "dup-a.md", early_entry, memory_dir=tmp_path)
        storage.write_entry(tmp_path / "dup-b.md", late_entry, memory_dir=tmp_path)

        engine = MemoryEngine(memory_dir=tmp_path)
        with patch("owlbear_memory.engine._LOGGER") as mock_logger:
            engine.get_entries()
            # At least one warning call mentioning the duplicate UUID
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(_DEDUP_ID in call for call in warning_calls)

    def test_parse_errors_accumulate_across_reloads(self, tmp_path: Path) -> None:
        """Edge: parse_errors reflects cumulative count from latest reload."""
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.get_entries()  # prime cache
        assert engine.parse_errors == 0

        # Add a bad file — directory mtime will change
        (tmp_path / "bad.md").write_text("junk")
        engine.get_entries()

        assert engine.parse_errors == 1

    def test_mixed_valid_and_invalid_returns_only_valid(self, tmp_path: Path) -> None:
        """Edge: mix of valid and invalid files — only valid entries returned."""
        valid_entry = _make_entry(_CURATED_ID, MemoryState.CURATED)
        _write_entry(tmp_path, valid_entry)
        (tmp_path / "bad.md").write_text("not frontmatter")

        engine = MemoryEngine(memory_dir=tmp_path)
        entries = engine.get_entries()

        assert len(entries) == 1
        assert entries[0].id == _CURATED_ID
