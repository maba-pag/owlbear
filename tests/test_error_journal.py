"""Failing tests for ErrorJournal module (task #189, TDD RED phase).

Covers: ErrorEntry model (4), TypeAdapter round-trip (2),
ErrorJournal init (2), log/load (3), load edge cases (2),
rotation (2) = 15 tests total.

All tests fail on current HEAD because
``packages/orchestrator/src/owlbear_orchestrator/error_journal.py``
does not exist yet.

Interface per AC #189:
  ErrorEntry: frozen Pydantic model, 5 fields
  entry_adapter: TypeAdapter[ErrorEntry] at module level
  ErrorJournal.__init__(path: Path, max_entries: int) -> None
  ErrorJournal.log(entry: ErrorEntry) -> None
  ErrorJournal.load() -> list[ErrorEntry]
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from owlbear_orchestrator.error_journal import ErrorEntry, ErrorJournal, entry_adapter


# ---------------------------------------------------------------------------
# ErrorEntry model tests
# ---------------------------------------------------------------------------


class TestFromAC_ErrorEntry:  # noqa: N801
    """ErrorEntry: frozen ConfigDict, all 5 fields are str, rejects mutation."""

    def test_all_five_fields_present(self) -> None:
        entry = ErrorEntry(
            timestamp="2026-01-01T00:00:00Z",
            category="transient",
            method="call_agent",
            message="connection refused",
            session_id="sess-001",
        )
        assert entry.timestamp == "2026-01-01T00:00:00Z"
        assert entry.category == "transient"
        assert entry.method == "call_agent"
        assert entry.message == "connection refused"
        assert entry.session_id == "sess-001"

    def test_all_fields_are_strings(self) -> None:
        entry = ErrorEntry(
            timestamp="2026-01-01T00:00:00Z",
            category="auth",
            method="new_session",
            message="token expired",
            session_id="sess-002",
        )
        assert isinstance(entry.timestamp, str)
        assert isinstance(entry.category, str)
        assert isinstance(entry.method, str)
        assert isinstance(entry.message, str)
        assert isinstance(entry.session_id, str)

    @pytest.mark.parametrize(
        "field",
        ["timestamp", "category", "method", "message", "session_id"],
    )
    def test_frozen_rejects_mutation(self, field: str) -> None:
        entry = ErrorEntry(
            timestamp="2026-01-01T00:00:00Z",
            category="permanent",
            method="send_prompt",
            message="invalid input",
            session_id="sess-003",
        )
        with pytest.raises((TypeError, ValidationError)):
            setattr(entry, field, "mutated_value")

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises((TypeError, ValidationError)):
            ErrorEntry(  # type: ignore[call-arg]
                timestamp="2026-01-01T00:00:00Z",
                category="transient",
                # method is missing
                message="err",
                session_id="s1",
            )


# ---------------------------------------------------------------------------
# Module-level TypeAdapter tests
# ---------------------------------------------------------------------------


class TestFromAC_ErrorEntryAdapter:  # noqa: N801
    """entry_adapter: module-level TypeAdapter[ErrorEntry] for JSONL serialization."""

    def test_adapter_is_type_adapter_instance(self) -> None:
        assert isinstance(entry_adapter, TypeAdapter)

    def test_round_trip_serialize_deserialize(self) -> None:
        original = ErrorEntry(
            timestamp="2026-03-29T10:00:00Z",
            category="tool_semantic",
            method="call_agent",
            message="resource not found",
            session_id="sess-rt",
        )
        serialized = entry_adapter.dump_json(original)
        deserialized = entry_adapter.validate_json(serialized)
        assert deserialized == original

    def test_round_trip_produces_valid_json(self) -> None:
        entry = ErrorEntry(
            timestamp="2026-03-29T10:00:00Z",
            category="transient",
            method="new_session",
            message="timeout",
            session_id="sess-json",
        )
        as_bytes = entry_adapter.dump_json(entry)
        as_dict = json.loads(as_bytes)
        assert as_dict["timestamp"] == entry.timestamp
        assert as_dict["category"] == entry.category
        assert as_dict["method"] == entry.method
        assert as_dict["message"] == entry.message
        assert as_dict["session_id"] == entry.session_id


# ---------------------------------------------------------------------------
# ErrorJournal.__init__ tests
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalInit:  # noqa: N801
    """ErrorJournal: accepts Path + max_entries, does not create file eagerly."""

    def test_accepts_path_and_max_entries(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=100)
        assert journal is not None

    def test_does_not_create_file_eagerly(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        ErrorJournal(path=log_file, max_entries=100)
        assert not log_file.exists()


# ---------------------------------------------------------------------------
# ErrorJournal.log() and load() round-trip tests
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalLog:  # noqa: N801
    """log() appends a single JSONL line; load() retrieves it as ErrorEntry."""

    def _make_entry(self, idx: int = 0) -> ErrorEntry:
        return ErrorEntry(
            timestamp=f"2026-03-29T10:0{idx}:00Z",
            category="transient",
            method="call_agent",
            message=f"error {idx}",
            session_id=f"sess-{idx:03d}",
        )

    def test_log_appends_single_jsonl_line(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=10)
        journal.log(self._make_entry(0))
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_load_retrieves_entry_after_log(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=10)
        entry = self._make_entry(0)
        journal.log(entry)
        loaded = journal.load()
        assert len(loaded) == 1
        assert loaded[0] == entry

    def test_multiple_log_calls_accumulate_entries(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=100)
        entries = [self._make_entry(i) for i in range(5)]
        for e in entries:
            journal.log(e)
        loaded = journal.load()
        assert len(loaded) == 5
        assert loaded == entries


# ---------------------------------------------------------------------------
# ErrorJournal.load() edge-case tests
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalLoad:  # noqa: N801
    """load() returns [] when file does not exist or is empty."""

    def test_load_returns_empty_when_file_does_not_exist(self, tmp_path: Path) -> None:
        log_file = tmp_path / "nonexistent_errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=10)
        assert journal.load() == []

    def test_load_returns_empty_when_file_is_empty(self, tmp_path: Path) -> None:
        log_file = tmp_path / "empty_errors.jsonl"
        log_file.write_text("", encoding="utf-8")
        journal = ErrorJournal(path=log_file, max_entries=10)
        assert journal.load() == []


# ---------------------------------------------------------------------------
# ErrorJournal rotation tests
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalRotation:  # noqa: N801
    """Rotation: at max_entries+1 writes, file is trimmed to max_entries; newest are kept."""

    def _make_entry(self, idx: int) -> ErrorEntry:
        return ErrorEntry(
            timestamp=f"2026-03-29T{idx:02d}:00:00Z",
            category="permanent",
            method="send_prompt",
            message=f"rotation test entry {idx}",
            session_id=f"sess-rot-{idx:03d}",
        )

    def test_rotation_trims_to_max_entries(self, tmp_path: Path) -> None:
        max_entries = 5
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=max_entries)
        for i in range(max_entries + 1):
            journal.log(self._make_entry(i))
        loaded = journal.load()
        assert len(loaded) == max_entries

    def test_rotation_preserves_most_recent_entries(self, tmp_path: Path) -> None:
        max_entries = 3
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=max_entries)
        # Write max+1 = 4 entries (0, 1, 2, 3)
        entries = [self._make_entry(i) for i in range(max_entries + 1)]
        for e in entries:
            journal.log(e)
        loaded = journal.load()
        # Oldest entry (index 0) must be evicted; entries 1, 2, 3 must be present
        assert self._make_entry(0) not in loaded
        assert self._make_entry(max_entries) in loaded
        # Entries are in chronological order (oldest first among the kept ones)
        assert loaded == entries[1:]
