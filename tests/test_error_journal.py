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
    """log() appends a single JSONL line; load() retrieves it as ErrorEntry.

    Updated (retry #184): uses keyword-only interface per AC4.
    Positional entry= param is not in AC4; resolved builder BLOCK.
    """

    def test_log_appends_single_jsonl_line(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=10)
        journal.log(
            category="transient",
            method="call_agent",
            message="error 0",
            session_id="sess-000",
        )
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_load_retrieves_entry_after_log(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=10)
        journal.log(
            category="transient",
            method="call_agent",
            message="error 0",
            session_id="sess-000",
        )
        loaded = journal.load()
        assert len(loaded) == 1
        assert loaded[0].category == "transient"
        assert loaded[0].method == "call_agent"
        assert loaded[0].message == "error 0"
        assert loaded[0].session_id == "sess-000"

    def test_multiple_log_calls_accumulate_entries(self, tmp_path: Path) -> None:
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=100)
        for i in range(5):
            journal.log(
                category="transient",
                method="call_agent",
                message=f"error {i}",
                session_id=f"sess-{i:03d}",
            )
        loaded = journal.load()
        assert len(loaded) == 5
        for i, entry in enumerate(loaded):
            assert entry.category == "transient"
            assert entry.method == "call_agent"
            assert entry.message == f"error {i}"
            assert entry.session_id == f"sess-{i:03d}"


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
    """Rotation: at max_entries+1 writes, file is trimmed to max_entries; newest are kept.

    Updated (retry #184): uses keyword-only interface per AC4.
    """

    def test_rotation_trims_to_max_entries(self, tmp_path: Path) -> None:
        max_entries = 5
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=max_entries)
        for i in range(max_entries + 1):
            journal.log(
                category="permanent",
                method="send_prompt",
                message=f"rotation test entry {i}",
                session_id=f"sess-rot-{i:03d}",
            )
        loaded = journal.load()
        assert len(loaded) == max_entries

    def test_rotation_preserves_most_recent_entries(self, tmp_path: Path) -> None:
        max_entries = 3
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file, max_entries=max_entries)
        # Write max+1 = 4 entries (0, 1, 2, 3)
        for i in range(max_entries + 1):
            journal.log(
                category="permanent",
                method="send_prompt",
                message=f"rotation test entry {i}",
                session_id=f"sess-rot-{i:03d}",
            )
        loaded = journal.load()
        # Oldest entry (index 0) must be evicted; entries 1, 2, 3 must be present
        messages = [e.message for e in loaded]
        assert "rotation test entry 0" not in messages
        assert f"rotation test entry {max_entries}" in messages
        # Entries are in chronological order (oldest first among the kept ones)
        assert messages == [f"rotation test entry {i}" for i in range(1, max_entries + 1)]


# ---------------------------------------------------------------------------
# #184 AC: keyword-only __init__ with default max_entries=5000
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalInitV2:  # noqa: N801
    """#184 AC: __init__(path, *, max_entries=5000) — keyword-only with default."""

    def test_default_max_entries_no_kwarg_required(self, tmp_path: Path) -> None:
        """ErrorJournal must work with just path; max_entries defaults to 5000."""
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file)
        assert journal is not None

    def test_max_entries_is_keyword_only(self, tmp_path: Path) -> None:
        """max_entries must be keyword-only: positional second arg must raise TypeError."""
        log_file = tmp_path / "errors.jsonl"
        with pytest.raises(TypeError):
            ErrorJournal(log_file, 100)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# #184 AC: keyword-only log(*, category, method, message, session_id) + auto-timestamp
# ---------------------------------------------------------------------------


class TestFromAC_ErrorJournalLogV2:  # noqa: N801
    """#184 AC: log(*, category, method, message, session_id) — keyword-only, auto-timestamp."""

    def test_log_accepts_keyword_args_no_entry_object(self, tmp_path: Path) -> None:
        """log() must accept keyword-only args; caller does not pass an ErrorEntry."""
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file)
        journal.log(
            category="transient",
            method="call_agent",
            message="timeout",
            session_id="sess-001",
        )
        assert log_file.exists()

    def test_log_auto_generates_iso8601_timestamp(self, tmp_path: Path) -> None:
        """log() must auto-generate a non-empty ISO-8601 timestamp; caller provides none."""
        from datetime import datetime

        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file)
        journal.log(
            category="transient",
            method="call_agent",
            message="timeout",
            session_id="sess-001",
        )
        loaded = journal.load()
        assert len(loaded) == 1
        ts = loaded[0].timestamp
        assert ts  # non-empty
        # Must be parseable as ISO-8601 (Python 3.11+ handles Z natively)
        datetime.fromisoformat(ts)

    def test_log_stores_all_four_caller_fields(self, tmp_path: Path) -> None:
        """All four keyword args (category, method, message, session_id) must be stored."""
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file)
        journal.log(
            category="permanent",
            method="send_prompt",
            message="invalid input",
            session_id="sess-xyz",
        )
        loaded = journal.load()
        assert len(loaded) == 1
        entry = loaded[0]
        assert entry.category == "permanent"
        assert entry.method == "send_prompt"
        assert entry.message == "invalid input"
        assert entry.session_id == "sess-xyz"

    def test_log_rotation_with_keyword_interface(self, tmp_path: Path) -> None:
        """Rotation still trims correctly when log() is called via keyword-only interface."""
        log_file = tmp_path / "errors.jsonl"
        max_e = 3
        journal = ErrorJournal(path=log_file, max_entries=max_e)
        for i in range(max_e + 1):
            journal.log(
                category="transient",
                method="call_agent",
                message=f"err {i}",
                session_id=f"sess-{i:03d}",
            )
        loaded = journal.load()
        assert len(loaded) == max_e
        assert loaded[-1].message == f"err {max_e}"  # most recent entry kept

    def test_log_positional_entry_object_raises_type_error(self, tmp_path: Path) -> None:
        """AC4: log(self, *, ...) — the * means NO positional args after self.
        Passing an ErrorEntry positionally must raise TypeError."""
        log_file = tmp_path / "errors.jsonl"
        journal = ErrorJournal(path=log_file)
        entry = ErrorEntry(
            timestamp="2026-01-01T00:00:00Z",
            category="transient",
            method="call_agent",
            message="err",
            session_id="sess-001",
        )
        with pytest.raises(TypeError):
            journal.log(entry)  # type: ignore[call-arg]  # positional — must raise
