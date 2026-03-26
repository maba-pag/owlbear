"""Tests for owlbear.memory.error_journal — ErrorJournal JSONL logger + query."""

from __future__ import annotations

import json
from pathlib import Path

from owlbear.core.jsonl_store import JsonlStore
from owlbear.memory.error_journal import ErrorEntry, ErrorJournal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_journal(tmp_path: Path) -> ErrorJournal:
    """Create an ErrorJournal pointing at a temp directory."""
    return ErrorJournal(workspace=tmp_path)


def _log_entry(  # noqa: PLR0913
    journal: ErrorJournal,
    *,
    ts: str = "2026-03-01T12:00:00Z",
    error_type: str = "transient",
    tool_name: str = "run_command",
    exc_message: str = "connection refused",
    action_taken: str = "retry",
    attempt: int = 1,
    resolved: bool = False,
    session_id: str = "sess-001",
) -> None:
    """Log a single entry with configurable defaults."""
    journal.log(
        ts=ts,
        error_type=error_type,
        tool_name=tool_name,
        exc_message=exc_message,
        action_taken=action_taken,
        attempt=attempt,
        resolved=resolved,
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------


class TestFileCreation:
    """ErrorJournal creates the JSONL file and parent directories."""

    def test_log_creates_parent_dirs(self, tmp_path: Path) -> None:
        journal = ErrorJournal(workspace=tmp_path / "deep" / "nested")
        _log_entry(journal)
        assert journal.path.exists()

    def test_path_is_under_owlbear_dir(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        assert journal.path == tmp_path / ".owlbear" / "error_journal.jsonl"

    def test_log_creates_file_on_first_write(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        assert not journal.path.exists()
        _log_entry(journal)
        assert journal.path.exists()


# ---------------------------------------------------------------------------
# Log entries
# ---------------------------------------------------------------------------


class TestLogEntries:
    """log() appends JSONL entries with expected fields."""

    def test_single_entry_is_valid_json(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal)
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert isinstance(entry, dict)

    def test_entry_has_all_fields(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal)
        entry = json.loads(journal.path.read_text(encoding="utf-8").strip())
        expected_keys = {
            "timestamp",
            "error_type",
            "tool_name",
            "exception_message",
            "action_taken",
            "attempt_number",
            "resolved",
            "session_id",
        }
        assert set(entry.keys()) == expected_keys

    def test_field_values_match_arguments(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        journal.log(
            ts="2026-03-01T12:00:00Z",
            error_type="auth",
            tool_name="delegate_to_agent",
            exc_message="token expired",
            action_taken="refresh",
            attempt=2,
            resolved=True,
            session_id="sess-042",
        )
        entry = json.loads(journal.path.read_text(encoding="utf-8").strip())
        assert entry["timestamp"] == "2026-03-01T12:00:00Z"
        assert entry["error_type"] == "auth"
        assert entry["tool_name"] == "delegate_to_agent"
        assert entry["exception_message"] == "token expired"
        assert entry["action_taken"] == "refresh"
        assert entry["attempt_number"] == 2
        assert entry["resolved"] is True
        assert entry["session_id"] == "sess-042"

    def test_multiple_entries_appended(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal, tool_name="tool_a")
        _log_entry(journal, tool_name="tool_b")
        _log_entry(journal, tool_name="tool_c")
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

    def test_entries_are_one_json_per_line(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal)
        _log_entry(journal)
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            json.loads(line)  # must not raise


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class TestQuery:
    """query() returns filtered entries."""

    def test_query_all_returns_all(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        for i in range(5):
            _log_entry(journal, tool_name=f"tool_{i}")
        results = journal.query()
        assert len(results) == 5

    def test_query_empty_journal(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        results = journal.query()
        assert results == []

    def test_query_filter_by_tool_name(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal, tool_name="run_command")
        _log_entry(journal, tool_name="delegate_to_agent")
        _log_entry(journal, tool_name="run_command")
        results = journal.query(tool_name="run_command")
        assert len(results) == 2
        assert all(r.tool_name == "run_command" for r in results)

    def test_query_filter_by_error_type(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal, error_type="transient")
        _log_entry(journal, error_type="auth")
        _log_entry(journal, error_type="transient")
        results = journal.query(error_type="transient")
        assert len(results) == 2

    def test_query_filter_by_both(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal, tool_name="run_command", error_type="transient")
        _log_entry(journal, tool_name="run_command", error_type="auth")
        _log_entry(journal, tool_name="delegate", error_type="transient")
        results = journal.query(tool_name="run_command", error_type="transient")
        assert len(results) == 1

    def test_query_last_n(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        for i in range(10):
            _log_entry(journal, tool_name=f"tool_{i}")
        results = journal.query(last_n=3)
        assert len(results) == 3
        # Should be the last 3 entries
        assert results[0].tool_name == "tool_7"
        assert results[2].tool_name == "tool_9"

    def test_query_last_n_with_filter(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal, tool_name="a", error_type="transient")
        _log_entry(journal, tool_name="b", error_type="auth")
        _log_entry(journal, tool_name="c", error_type="transient")
        _log_entry(journal, tool_name="d", error_type="transient")
        results = journal.query(error_type="transient", last_n=2)
        assert len(results) == 2
        assert results[0].tool_name == "c"
        assert results[1].tool_name == "d"

    def test_query_last_n_exceeds_count(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal)
        _log_entry(journal)
        results = journal.query(last_n=100)
        assert len(results) == 2

    def test_query_no_match(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal, tool_name="run_command")
        results = journal.query(tool_name="nonexistent")
        assert results == []

    def test_query_returns_error_entries(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        _log_entry(journal)
        results = journal.query()
        assert all(isinstance(r, ErrorEntry) for r in results)


# ---------------------------------------------------------------------------
# Rotation (10K entry cap)
# ---------------------------------------------------------------------------


class TestRotation:
    """10K entry cap with rotation — keeps last 10K entries."""

    def test_no_rotation_under_cap(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        for i in range(100):
            _log_entry(journal, tool_name=f"tool_{i}")
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 100

    def test_rotation_at_cap(self, tmp_path: Path) -> None:
        journal = ErrorJournal(workspace=tmp_path, max_entries=50)
        for i in range(60):
            _log_entry(journal, tool_name=f"tool_{i}")
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 50

    def test_rotation_keeps_latest(self, tmp_path: Path) -> None:
        journal = ErrorJournal(workspace=tmp_path, max_entries=50)
        for i in range(60):
            _log_entry(journal, tool_name=f"tool_{i}")
        results = journal.query()
        # Should have entries tool_10 through tool_59 (the last 50)
        assert results[0].tool_name == "tool_10"
        assert results[-1].tool_name == "tool_59"

    def test_rotation_triggers_on_log(self, tmp_path: Path) -> None:
        """Rotation happens during log(), not lazily."""
        journal = ErrorJournal(workspace=tmp_path, max_entries=10)
        for i in range(15):
            _log_entry(journal, tool_name=f"tool_{i}")
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 10

    def test_default_cap_is_10000(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        assert journal.max_entries == 10_000


# ---------------------------------------------------------------------------
# Model + inheritance
# ---------------------------------------------------------------------------


class TestModelAndInheritance:
    """ErrorEntry is a BaseModel and ErrorJournal inherits JsonlStore."""

    def test_error_journal_is_jsonl_store(self, tmp_path: Path) -> None:
        journal = _make_journal(tmp_path)
        assert isinstance(journal, JsonlStore)

    def test_error_entry_has_expected_fields(self) -> None:
        entry = ErrorEntry(
            timestamp="2026-03-01T12:00:00Z",
            error_type="transient",
            tool_name="run_command",
            exception_message="connection refused",
            action_taken="retry",
            attempt_number=1,
            resolved=False,
            session_id="sess-001",
        )
        assert entry.timestamp == "2026-03-01T12:00:00Z"
        assert entry.attempt_number == 1
        assert entry.resolved is False
