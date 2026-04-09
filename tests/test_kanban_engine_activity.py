"""Failing tests for activity.jsonl append-only logging (#727, RED phase).

AC coverage:
  AC1 - log entry format: {"timestamp":"<ISO>","action":"<verb>","task_id":<int>,"detail":"<string>"}
  AC2 - each action verb (create, edit, move, claim, release, block, unblock)
        produces correct log entry
  AC3 - append-only semantics: new entries appended, existing untouched
  AC4 - log file created if missing
  AC5 - all tests fail (RED gate)

Import path: owlbear_mcp_kanban.activity_log (module does NOT exist yet — #728 will create it).
All tests must FAIL at this stage — GREEN phase is task #728.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from owlbear_mcp_kanban.activity_log import log_activity  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_entries(log_path: Path) -> list[dict]:
    """Parse a JSONL file into a list of dicts."""
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ===========================================================================
# TestFromAC_LogEntryFormat — AC1: exact JSON schema
# ===========================================================================


class TestFromAC_LogEntryFormat:
    """Tests for AC1: each log entry is valid JSON with exactly the required keys."""

    def test_entry_is_valid_json(self, tmp_path: Path) -> None:
        """A single log_activity call writes a parseable JSON line."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 42, "created task")
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        json.loads(lines[0])  # must not raise

    def test_entry_has_exactly_four_keys(self, tmp_path: Path) -> None:
        """Log entry contains exactly: timestamp, action, task_id, detail — no extra keys."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        assert set(entry.keys()) == {"timestamp", "action", "task_id", "detail"}

    def test_entry_timestamp_key_present(self, tmp_path: Path) -> None:
        """Log entry contains 'timestamp' key."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        assert "timestamp" in entry

    def test_entry_timestamp_is_iso_parseable(self, tmp_path: Path) -> None:
        """Timestamp value is parseable as ISO 8601 datetime."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        # Must not raise
        datetime.fromisoformat(entry["timestamp"])

    def test_entry_action_is_string(self, tmp_path: Path) -> None:
        """action field is a str."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "edit", 5, "changed title")
        entry = _read_entries(log_path)[0]
        assert isinstance(entry["action"], str)

    def test_entry_action_matches_argument(self, tmp_path: Path) -> None:
        """action in log matches the action argument passed."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "move", 3, "todo -> in-progress")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == "move"

    def test_entry_task_id_is_integer(self, tmp_path: Path) -> None:
        """task_id field is an int, not a string."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 99, "detail")
        entry = _read_entries(log_path)[0]
        assert isinstance(entry["task_id"], int)

    def test_entry_task_id_matches_argument(self, tmp_path: Path) -> None:
        """task_id in log matches the task_id argument."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 42, "detail")
        entry = _read_entries(log_path)[0]
        assert entry["task_id"] == 42

    def test_entry_detail_is_string(self, tmp_path: Path) -> None:
        """detail field is a str."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "some detail string")
        entry = _read_entries(log_path)[0]
        assert isinstance(entry["detail"], str)

    def test_entry_detail_matches_argument(self, tmp_path: Path) -> None:
        """detail in log matches the detail argument."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "my detail text")
        entry = _read_entries(log_path)[0]
        assert entry["detail"] == "my detail text"

    def test_entry_timestamp_is_string_type(self, tmp_path: Path) -> None:
        """timestamp field is a str (not a datetime object embedded in JSON)."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        assert isinstance(entry["timestamp"], str)


# ===========================================================================
# TestFromAC_ActionVerbs — AC2: all 7 authorised verbs
# Authoritative list (arch review vocab resolution): create, edit, move, claim,
# release, block, unblock — NO archive verb (archive ops log as move).
# ===========================================================================


class TestFromAC_ActionVerbs:
    """Tests for AC2: each of the 7 authorised verbs is stored verbatim in action."""

    @pytest.mark.parametrize(
        "verb",
        ["create", "edit", "move", "claim", "release", "block", "unblock"],
    )
    def test_verb_written_to_action_field(self, tmp_path: Path, verb: str) -> None:
        """Each authorised verb is stored verbatim in the action field."""
        log_path = tmp_path / f"activity_{verb}.jsonl"
        log_activity(log_path, verb, 10, f"{verb} detail")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == verb

    def test_create_verb_preserves_task_id(self, tmp_path: Path) -> None:
        """create verb log includes correct task_id."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 100, "New task: Foo")
        entry = _read_entries(log_path)[0]
        assert entry["task_id"] == 100

    def test_move_verb_preserves_transition_detail(self, tmp_path: Path) -> None:
        """move verb preserves transition string in detail."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "move", 5, "todo -> in-progress")
        entry = _read_entries(log_path)[0]
        assert entry["detail"] == "todo -> in-progress"

    def test_claim_verb_full_entry(self, tmp_path: Path) -> None:
        """claim verb produces a well-formed entry with correct action and task_id."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "claim", 7, "claimed by agent")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == "claim"
        assert entry["task_id"] == 7

    def test_release_verb_full_entry(self, tmp_path: Path) -> None:
        """release verb produces a well-formed entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "release", 7, "released: success")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == "release"
        assert entry["task_id"] == 7

    def test_block_verb_full_entry(self, tmp_path: Path) -> None:
        """block verb produces a well-formed entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "block", 3, "blocked: waiting for #4")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == "block"
        assert entry["task_id"] == 3

    def test_unblock_verb_full_entry(self, tmp_path: Path) -> None:
        """unblock verb produces a well-formed entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "unblock", 3, "unblocked: #4 resolved")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == "unblock"
        assert entry["task_id"] == 3

    def test_edit_verb_full_entry(self, tmp_path: Path) -> None:
        """edit verb produces a well-formed entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "edit", 20, "title changed")
        entry = _read_entries(log_path)[0]
        assert entry["action"] == "edit"
        assert entry["task_id"] == 20


# ===========================================================================
# TestFromAC_AppendOnlySemantics — AC3
# ===========================================================================


class TestFromAC_AppendOnlySemantics:
    """Tests for AC3: entries are appended; prior entries are never mutated."""

    def test_two_calls_produce_two_lines(self, tmp_path: Path) -> None:
        """Two calls produce exactly two JSONL lines."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "first")
        log_activity(log_path, "edit", 1, "second")
        assert len(_read_entries(log_path)) == 2

    def test_entries_in_insertion_order(self, tmp_path: Path) -> None:
        """Earlier entry appears before later entry in the file."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "first")
        log_activity(log_path, "edit", 1, "second")
        entries = _read_entries(log_path)
        assert entries[0]["detail"] == "first"
        assert entries[1]["detail"] == "second"

    def test_first_entry_untouched_after_second_append(self, tmp_path: Path) -> None:
        """First entry's action and detail are unchanged after a second call."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 10, "original detail")
        log_activity(log_path, "move", 10, "something else")
        entries = _read_entries(log_path)
        assert entries[0]["action"] == "create"
        assert entries[0]["detail"] == "original detail"

    def test_second_entry_action_is_independent(self, tmp_path: Path) -> None:
        """Second entry's action reflects the second call's verb, not the first."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 5, "first")
        log_activity(log_path, "claim", 5, "second")
        entries = _read_entries(log_path)
        assert entries[1]["action"] == "claim"

    def test_ten_appends_produce_ten_entries(self, tmp_path: Path) -> None:
        """10 sequential calls produce exactly 10 JSONL entries."""
        log_path = tmp_path / "activity.jsonl"
        verbs = ["create", "edit", "move", "claim", "release", "block", "unblock",
                 "edit", "move", "edit"]
        for i, verb in enumerate(verbs):
            log_activity(log_path, verb, i, f"entry {i}")
        entries = _read_entries(log_path)
        assert len(entries) == 10

    def test_each_entry_has_distinct_task_id_when_varied(self, tmp_path: Path) -> None:
        """Entries preserve distinct task_ids when called with different ids."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "task one")
        log_activity(log_path, "create", 2, "task two")
        entries = _read_entries(log_path)
        assert entries[0]["task_id"] == 1
        assert entries[1]["task_id"] == 2


# ===========================================================================
# TestFromAC_LogFileMissing — AC4: file created if missing
# ===========================================================================


class TestFromAC_LogFileMissing:
    """Tests for AC4: log file is created when it does not already exist."""

    def test_log_file_created_when_absent(self, tmp_path: Path) -> None:
        """log_activity creates the file when file does not exist."""
        log_path = tmp_path / "activity.jsonl"
        assert not log_path.exists()
        log_activity(log_path, "create", 1, "first entry")
        assert log_path.exists()

    def test_first_write_produces_one_line(self, tmp_path: Path) -> None:
        """Brand-new log file has exactly one line after a single call."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 7, "only entry")
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

    def test_log_file_created_for_every_verb(self, tmp_path: Path) -> None:
        """Each verb is capable of creating a fresh log file."""
        for i, verb in enumerate(
            ["create", "edit", "move", "claim", "release", "block", "unblock"]
        ):
            log_path = tmp_path / f"activity_{verb}.jsonl"
            assert not log_path.exists()
            log_activity(log_path, verb, i, f"{verb} creates file")
            assert log_path.exists()

    def test_existing_file_not_truncated_on_new_call(self, tmp_path: Path) -> None:
        """An existing log file is not wiped when a new entry is appended."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "pre-existing entry")
        log_activity(log_path, "edit", 1, "new entry")
        entries = _read_entries(log_path)
        # Both entries must survive — not just the last
        assert len(entries) == 2
        assert entries[0]["detail"] == "pre-existing entry"


# ===========================================================================
# TestFromAC_BoundaryConditions — edge / boundary (implied by AC)
# ===========================================================================


class TestFromAC_BoundaryConditions:
    """Boundary and edge-case tests implied by AC but not explicitly listed."""

    def test_empty_detail_stored_as_empty_string(self, tmp_path: Path) -> None:
        """An empty detail is stored as '' in the JSON entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "")
        entry = _read_entries(log_path)[0]
        assert entry["detail"] == ""

    def test_large_task_id_stored_without_truncation(self, tmp_path: Path) -> None:
        """A very large task_id is stored exactly as the int passed."""
        log_path = tmp_path / "activity.jsonl"
        large_id = 999_999_999
        log_activity(log_path, "create", large_id, "big id")
        entry = _read_entries(log_path)[0]
        assert entry["task_id"] == large_id

    def test_detail_with_json_special_characters(self, tmp_path: Path) -> None:
        """detail containing quotes and backslashes survives JSON round-trip."""
        log_path = tmp_path / "activity.jsonl"
        detail = 'title changed to "foo\\bar"'
        log_activity(log_path, "edit", 1, detail)
        entry = _read_entries(log_path)[0]
        assert entry["detail"] == detail

    def test_task_id_of_zero_stored_as_int_zero(self, tmp_path: Path) -> None:
        """task_id of 0 is stored as int 0, not omitted or converted to null."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 0, "zero id")
        entry = _read_entries(log_path)[0]
        assert entry["task_id"] == 0
        assert isinstance(entry["task_id"], int)
