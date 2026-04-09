"""Failing tests for KanbanEngine activity.jsonl wiring (#728, RED phase).

AC coverage:
  AC-INIT  - Engine.__init__ stores self._activity_log_path = kanban_dir / "activity.jsonl"
  AC-CREATE - create_task logs action="create", detail=title
  AC-EDIT   - edit_task logs action="edit", detail=summary of changed fields
  AC-MOVE   - move_task (non-archive) logs action="move", detail="{old} -> {new}"
  AC-ARCH   - move_task (status="archived") logs action="move", detail="{old} -> archived"
  AC-CLAIM  - claim_task logs action="claim", detail=agent_name
  AC-RELEAS - release_task logs action="release", detail=agent_name
  AC-BLOCK  - edit_task(blocked False→True) logs action="block", detail=block_reason or ""
  AC-UNBLK  - edit_task(blocked True→False) logs action="unblock", detail=""
  AC-DETECT - block/unblock detection emits block/unblock INSTEAD OF edit on transition
  AC-FILE   - log file created on first write if missing

All tests must FAIL — GREEN phase is task #728.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlbear_mcp_kanban.engine import KanbanEngine

# ---------------------------------------------------------------------------
# Config + fixtures
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: review
    - name: docs
    - name: done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
defaults:
    status: research
    priority: important
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 100
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine wired to temp kanban_dir with fixed agent_name."""
    return KanbanEngine(kanban_dir, agent_name="test-agent")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_entries(log_path: Path) -> list[dict]:
    """Parse a JSONL file into a list of dicts. Returns [] if the file is missing."""
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _reset_log(kanban_dir: Path) -> None:
    """Remove activity.jsonl so subsequent assertions start with a clean slate."""
    (kanban_dir / "activity.jsonl").unlink(missing_ok=True)


# ===========================================================================
# TestFromAC_ActivityLogPath — AC-INIT
# ===========================================================================


class TestFromAC_ActivityLogPath:
    """Engine.__init__ stores _activity_log_path = kanban_dir / 'activity.jsonl'."""

    def test_engine_has_activity_log_path_attribute(
        self, engine: KanbanEngine
    ) -> None:
        """_activity_log_path attribute exists on the engine instance."""
        assert hasattr(engine, "_activity_log_path"), (
            "Engine should expose _activity_log_path after __init__"
        )

    def test_activity_log_path_points_to_jsonl_in_kanban_dir(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """_activity_log_path resolves to kanban_dir / 'activity.jsonl'."""
        assert hasattr(engine, "_activity_log_path")
        assert engine._activity_log_path == kanban_dir / "activity.jsonl"


# ===========================================================================
# TestFromAC_CreateTaskLogging — AC-CREATE
# ===========================================================================


class TestFromAC_CreateTaskLogging:
    """create_task → action='create', detail=title."""

    def test_create_task_writes_log_entry(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """create_task produces exactly one entry in activity.jsonl."""
        engine.create_task("Brand New Task")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert len(entries) == 1

    def test_create_task_log_action_is_create(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """create_task log entry action field is 'create'."""
        engine.create_task("Some Task")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after create_task"
        assert entries[0]["action"] == "create"

    def test_create_task_log_detail_equals_title(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """create_task log detail equals the task title."""
        engine.create_task("Exact Title Here")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after create_task"
        assert entries[0]["detail"] == "Exact Title Here"

    def test_create_task_log_task_id_matches_record(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """create_task log task_id matches the newly created task's id."""
        record = engine.create_task("Task Alpha")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after create_task"
        assert entries[0]["task_id"] == record.id

    def test_two_creates_append_two_entries(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Two create_task calls append two log entries in order."""
        engine.create_task("First")
        engine.create_task("Second")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert len(entries) == 2
        assert entries[0]["detail"] == "First"
        assert entries[1]["detail"] == "Second"


# ===========================================================================
# TestFromAC_EditTaskLogging — AC-EDIT
# ===========================================================================


class TestFromAC_EditTaskLogging:
    """edit_task (no blocked transition) → action='edit', detail=changed fields."""

    def test_edit_task_writes_log_entry(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task produces an entry in activity.jsonl."""
        record = engine.create_task("Editable")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), title="Renamed")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert len(entries) == 1

    def test_edit_task_log_action_is_edit(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task logs action='edit'."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), title="Changed Title")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after edit_task"
        assert entries[0]["action"] == "edit"

    def test_edit_task_log_task_id_matches(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task log task_id matches the edited task's id."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), body="updated body")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after edit_task"
        assert entries[0]["task_id"] == record.id

    def test_edit_task_log_detail_is_non_empty_string(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task detail is a non-empty string summarising changed fields."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), priority="critical")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after edit_task"
        assert isinstance(entries[0]["detail"], str)
        assert len(entries[0]["detail"]) > 0


# ===========================================================================
# TestFromAC_MoveTaskLogging — AC-MOVE + AC-ARCH
# ===========================================================================


class TestFromAC_MoveTaskLogging:
    """move_task logs action='move' with '{old} -> {new}' detail."""

    def test_move_task_writes_log_entry(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """move_task produces an entry in activity.jsonl."""
        record = engine.create_task("Moveable")
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "todo")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert len(entries) == 1

    def test_move_task_log_action_is_move(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """move_task logs action='move'."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "backlog")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after move_task"
        assert entries[0]["action"] == "move"

    def test_move_task_detail_shows_status_transition(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """move_task detail is '{old_status} -> {new_status}'."""
        record = engine.create_task("Task")  # default status: research
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "todo")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after move_task"
        assert entries[0]["detail"] == "research -> todo"

    def test_move_task_log_task_id_matches(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """move_task log task_id matches the moved task's id."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "done")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after move_task"
        assert entries[0]["task_id"] == record.id

    def test_archive_uses_move_verb_not_archive(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Archiving logs action='move', NOT action='archive'."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "archived")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after archiving"
        assert entries[0]["action"] == "move"

    def test_archive_detail_shows_archived_destination(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Archiving detail is '{old_status} -> archived'."""
        record = engine.create_task("Task")  # default status: research
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "archived")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after archiving"
        assert entries[0]["detail"] == "research -> archived"


# ===========================================================================
# TestFromAC_ClaimTaskLogging — AC-CLAIM
# ===========================================================================


class TestFromAC_ClaimTaskLogging:
    """claim_task → action='claim', detail=agent_name."""

    def test_claim_task_writes_log_entry(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """claim_task produces an entry in activity.jsonl."""
        record = engine.create_task("Claimable")
        _reset_log(kanban_dir)
        engine.claim_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert len(entries) == 1

    def test_claim_task_log_action_is_claim(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """claim_task logs action='claim'."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.claim_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after claim_task"
        assert entries[0]["action"] == "claim"

    def test_claim_task_log_detail_is_agent_name(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """claim_task detail is the engine's agent_name."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.claim_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after claim_task"
        assert entries[0]["detail"] == engine.agent_name

    def test_claim_task_log_task_id_matches(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """claim_task log task_id matches the claimed task's id."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.claim_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after claim_task"
        assert entries[0]["task_id"] == record.id


# ===========================================================================
# TestFromAC_ReleaseTaskLogging — AC-RELEAS
# ===========================================================================


class TestFromAC_ReleaseTaskLogging:
    """release_task → action='release', detail=agent_name."""

    def test_release_task_writes_log_entry(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """release_task produces an entry in activity.jsonl."""
        record = engine.create_task("Releasable")
        engine.claim_task(str(record.id))
        _reset_log(kanban_dir)
        engine.release_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert len(entries) == 1

    def test_release_task_log_action_is_release(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """release_task logs action='release'."""
        record = engine.create_task("Task")
        engine.claim_task(str(record.id))
        _reset_log(kanban_dir)
        engine.release_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after release_task"
        assert entries[0]["action"] == "release"

    def test_release_task_log_detail_is_agent_name(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """release_task detail is the engine's agent_name."""
        record = engine.create_task("Task")
        engine.claim_task(str(record.id))
        _reset_log(kanban_dir)
        engine.release_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after release_task"
        assert entries[0]["detail"] == engine.agent_name

    def test_release_task_log_task_id_matches(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """release_task log task_id matches the released task's id."""
        record = engine.create_task("Task")
        engine.claim_task(str(record.id))
        _reset_log(kanban_dir)
        engine.release_task(str(record.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after release_task"
        assert entries[0]["task_id"] == record.id


# ===========================================================================
# TestFromAC_BlockUnblockDetection — AC-BLOCK + AC-UNBLK + AC-DETECT
# ===========================================================================


class TestFromAC_BlockUnblockDetection:
    """Block/unblock transitions emit 'block'/'unblock' INSTEAD OF 'edit'."""

    def test_false_to_true_transition_emits_block(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task(blocked=True) on unblocked task logs action='block'."""
        record = engine.create_task("Blockable")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=True, block_reason="dep missing")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after blocking"
        assert entries[0]["action"] == "block"

    def test_block_detail_equals_block_reason(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task(blocked=True) detail is the block_reason string."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=True, block_reason="needs approval")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after blocking"
        assert entries[0]["detail"] == "needs approval"

    def test_block_without_reason_uses_empty_detail(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task(blocked=True) with no block_reason logs detail=''."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=True)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after blocking"
        assert entries[0]["action"] == "block"
        assert entries[0]["detail"] == ""

    def test_true_to_false_transition_emits_unblock(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task(blocked=False) on blocked task logs action='unblock'."""
        record = engine.create_task("Task")
        engine.edit_task(str(record.id), blocked=True, block_reason="reason")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=False)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after unblocking"
        assert entries[0]["action"] == "unblock"

    def test_unblock_detail_is_empty_string(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task(blocked=False) on blocked task logs detail=''."""
        record = engine.create_task("Task")
        engine.edit_task(str(record.id), blocked=True, block_reason="reason")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=False)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after unblocking"
        assert entries[0]["detail"] == ""

    def test_block_emits_block_not_edit(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Block transition emits 'block' and NOT 'edit' — INSTEAD-OF contract."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=True)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after blocking"
        assert entries[0]["action"] != "edit"

    def test_unblock_emits_unblock_not_edit(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Unblock transition emits 'unblock' and NOT 'edit' — INSTEAD-OF contract."""
        record = engine.create_task("Task")
        engine.edit_task(str(record.id), blocked=True)
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=False)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after unblocking"
        assert entries[0]["action"] != "edit"

    def test_block_transition_with_simultaneous_field_change_still_emits_block(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Block wins over edit even when title also changes in same call."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), title="New Title", blocked=True, block_reason="r")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry"
        assert entries[0]["action"] == "block"

    def test_no_blocked_transition_emits_edit(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task with no blocked state change (False→False) emits 'edit', not 'unblock'."""
        record = engine.create_task("Task")  # blocked=False by default
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), title="Changed", blocked=False)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after edit_task"
        assert entries[0]["action"] == "edit"

    def test_block_log_task_id_matches(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Block log entry task_id matches the blocked task's id."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=True)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        assert entries, "Expected a log entry after blocking"
        assert entries[0]["task_id"] == record.id


# ===========================================================================
# TestFromAC_LogFileCreation — AC-FILE
# ===========================================================================


class TestFromAC_LogFileCreation:
    """Log file is created on first write if it does not exist beforehand."""

    def test_log_file_created_by_first_create_task(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """activity.jsonl is created when create_task is called for the first time."""
        log_path = kanban_dir / "activity.jsonl"
        assert not log_path.exists(), "Precondition: file must not exist yet"
        engine.create_task("First Task")
        assert log_path.exists()

    def test_log_file_created_by_first_move_task(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """Deleting the log then calling move_task recreates activity.jsonl."""
        record = engine.create_task("Task")
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "todo")
        assert (kanban_dir / "activity.jsonl").exists()
