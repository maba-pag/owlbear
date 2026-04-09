"""Failing tests for KanbanEngine compound operations: start_work and end_work (#725, RED phase).

AC coverage:
  AC1 - start_work: blocked guard, claim, return full task
  AC2 - end_work(success): append timestamped note, advance to next status, release claim
  AC3 - end_work(success) on last status: archive task
  AC4 - end_work(fail): append note, keep status, release claim
  AC5 - end_work(block): append note, set blocked=True + reason, release claim
  AC6 - end_work(reject): append note, move to specified status, release claim
  AC7 - end_work without block_reason when outcome=block raises error

All tests must FAIL at this stage — GREEN phase follows.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from owlbear_mcp_kanban.engine import KanbanEngine  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Shared config content — mirrors real .owlbear/kanban/config.yml
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine with a pinned agent_name for deterministic tests."""
    return KanbanEngine(kanban_dir, agent_name="alpha-test")


# ===========================================================================
# TestFromAC_StartWork — AC1
# ===========================================================================


class TestFromAC_StartWork:
    """Tests for AC1: start_work blocked guard, claim, return full task."""

    def test_start_work_returns_task_record(self, engine: KanbanEngine) -> None:
        """start_work returns a TaskRecord whose id matches the created task."""
        task = engine.create_task("Compound work task")
        result = engine.start_work(str(task.id))
        assert result.id == task.id

    def test_start_work_returns_full_record_with_title(self, engine: KanbanEngine) -> None:
        """Returned record includes task title — full record, not a stub."""
        task = engine.create_task("Named task for start_work")
        result = engine.start_work(str(task.id))
        assert result.title == "Named task for start_work"

    def test_start_work_sets_claimed_by(self, engine: KanbanEngine) -> None:
        """start_work claims the task: claimed_by equals engine.agent_name."""
        task = engine.create_task("Claim via start_work")
        engine.start_work(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_by == engine.agent_name

    def test_start_work_sets_claimed_at_as_iso_string(self, engine: KanbanEngine) -> None:
        """start_work sets claimed_at as a parseable ISO datetime string."""
        from datetime import datetime

        task = engine.create_task("Timestamp via start_work")
        engine.start_work(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_at is not None
        datetime.fromisoformat(record.claimed_at)  # must not raise

    def test_start_work_blocked_task_raises_value_error(self, engine: KanbanEngine) -> None:
        """start_work raises ValueError for a blocked task (blocked guard)."""
        task = engine.create_task("Blocked task")
        engine.edit_task(str(task.id), blocked=True, block_reason="pending dependency")
        with pytest.raises(ValueError, match="blocked"):  # noqa: PT011
            engine.start_work(str(task.id))

    def test_start_work_blocked_does_not_expose_task_as_claimed(
        self, engine: KanbanEngine
    ) -> None:
        """Rejected start_work on blocked task leaves claimed_by as None."""
        task = engine.create_task("Blocked unclaimed")
        engine.edit_task(str(task.id), blocked=True, block_reason="dependency missing")
        with pytest.raises(ValueError):  # noqa: PT011
            engine.start_work(str(task.id))
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None

    def test_start_work_nonexistent_task_raises(self, engine: KanbanEngine) -> None:
        """start_work raises when the task ID does not exist."""
        with pytest.raises(FileNotFoundError):
            engine.start_work("9999")


# ===========================================================================
# TestFromAC_EndWorkSuccess — AC2
# ===========================================================================


class TestFromAC_EndWorkSuccess:
    """Tests for AC2: end_work(success) appends timestamped note, advances status, releases claim."""

    def test_end_work_success_appends_note_to_body(self, engine: KanbanEngine) -> None:
        """Note text is appended to the task body after end_work(success)."""
        task = engine.create_task("Task with note")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Work complete", outcome="success")
        record = engine.show_task(str(task.id))
        assert "Work complete" in record.body

    def test_end_work_success_note_has_timestamp_prefix(self, engine: KanbanEngine) -> None:
        """Appended note is prefixed with a [[YYYY-MM-DD]] timestamp."""
        task = engine.create_task("Timestamp check task")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Timestamped note", outcome="success")
        record = engine.show_task(str(task.id))
        assert re.search(r"\[\[\d{4}-\d{2}-\d{2}\]\]", record.body)

    def test_end_work_success_advances_status_from_research(
        self, engine: KanbanEngine
    ) -> None:
        """end_work(success) moves task from 'research' to 'backlog'."""
        task = engine.create_task("Advance task", status="research")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Done", outcome="success")
        record = engine.show_task(str(task.id))
        assert record.status == "backlog"

    def test_end_work_success_advances_status_mid_chain(self, engine: KanbanEngine) -> None:
        """end_work(success) when at 'in-progress' advances exactly one step to 'review'."""
        task = engine.create_task("Mid-chain task", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Review ready", outcome="success")
        record = engine.show_task(str(task.id))
        assert record.status == "review"

    def test_end_work_success_penultimate_advances_to_last_status(
        self, engine: KanbanEngine
    ) -> None:
        """end_work(success) when at 'docs' (penultimate) advances to 'done' (last)."""
        task = engine.create_task("Pre-last task", status="docs")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Final step", outcome="success")
        record = engine.show_task(str(task.id))
        assert record.status == "done"

    def test_end_work_success_releases_claim(self, engine: KanbanEngine) -> None:
        """end_work(success) clears claimed_by and claimed_at."""
        task = engine.create_task("Release after success")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Released", outcome="success")
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None
        assert record.claimed_at is None

    def test_end_work_success_returns_task_record(self, engine: KanbanEngine) -> None:
        """end_work(success) returns a TaskRecord with the updated status."""
        task = engine.create_task("Return check", status="backlog")
        engine.start_work(str(task.id))
        result = engine.end_work(str(task.id), note="Return check", outcome="success")
        assert result.id == task.id
        assert result.status == "todo"


# ===========================================================================
# TestFromAC_EndWorkSuccessLastStatus — AC3
# ===========================================================================


class TestFromAC_EndWorkSuccessLastStatus:
    """Tests for AC3: end_work(success) on last status archives the task."""

    def test_end_work_last_status_removes_from_tasks_dir(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """end_work(success) on 'done' (last status) removes file from tasks/."""
        task = engine.create_task("Archive me", status="done")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Archiving", outcome="success")
        tasks_dir = kanban_dir / "tasks"
        task_files = list(tasks_dir.glob(f"{task.id}-*.md"))
        assert task_files == []

    def test_end_work_last_status_creates_file_in_archive_dir(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """end_work(success) on 'done' creates the task file in v1-archive/."""
        task = engine.create_task("Find in archive", status="done")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Archived note", outcome="success")
        archive_dir = kanban_dir / "v1-archive"
        archive_files = list(archive_dir.glob(f"{task.id}-*.md"))
        assert len(archive_files) == 1

    def test_end_work_last_status_note_present_in_archive(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """The appended note is present in the archived task file."""
        task = engine.create_task("Note in archive", status="done")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Final note text", outcome="success")
        archive_dir = kanban_dir / "v1-archive"
        archive_files = list(archive_dir.glob(f"{task.id}-*.md"))
        assert archive_files
        content = archive_files[0].read_text(encoding="utf-8")
        assert "Final note text" in content


# ===========================================================================
# TestFromAC_EndWorkFail — AC4
# ===========================================================================


class TestFromAC_EndWorkFail:
    """Tests for AC4: end_work(fail) appends note, keeps status, releases claim."""

    def test_end_work_fail_appends_note(self, engine: KanbanEngine) -> None:
        """Note is appended to task body after end_work(fail)."""
        task = engine.create_task("Fail note task", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Blocked by upstream", outcome="fail")
        record = engine.show_task(str(task.id))
        assert "Blocked by upstream" in record.body

    def test_end_work_fail_keeps_status(self, engine: KanbanEngine) -> None:
        """end_work(fail) leaves the task status unchanged."""
        task = engine.create_task("Status preserved", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Still in progress", outcome="fail")
        record = engine.show_task(str(task.id))
        assert record.status == "in-progress"

    def test_end_work_fail_releases_claimed_by(self, engine: KanbanEngine) -> None:
        """end_work(fail) clears claimed_by."""
        task = engine.create_task("Release on fail", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Releasing", outcome="fail")
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None

    def test_end_work_fail_releases_claimed_at(self, engine: KanbanEngine) -> None:
        """end_work(fail) clears claimed_at."""
        task = engine.create_task("Release timestamp on fail", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Releasing", outcome="fail")
        record = engine.show_task(str(task.id))
        assert record.claimed_at is None

    def test_end_work_fail_returns_task_record(self, engine: KanbanEngine) -> None:
        """end_work(fail) returns a TaskRecord with the unchanged status."""
        task = engine.create_task("Return on fail", status="todo")
        engine.start_work(str(task.id))
        result = engine.end_work(str(task.id), note="Return check", outcome="fail")
        assert result.id == task.id
        assert result.status == "todo"


# ===========================================================================
# TestFromAC_EndWorkBlock — AC5
# ===========================================================================


class TestFromAC_EndWorkBlock:
    """Tests for AC5: end_work(block) appends note, sets blocked + reason, releases claim."""

    def test_end_work_block_appends_note(self, engine: KanbanEngine) -> None:
        """Note is appended to task body after end_work(block)."""
        task = engine.create_task("Block note task", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Waiting on data", outcome="block", block_reason="dep pending"
        )
        record = engine.show_task(str(task.id))
        assert "Waiting on data" in record.body

    def test_end_work_block_sets_blocked_true(self, engine: KanbanEngine) -> None:
        """end_work(block) sets blocked=True on the task."""
        task = engine.create_task("Block flag task", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Blocked", outcome="block", block_reason="infra down"
        )
        record = engine.show_task(str(task.id))
        assert record.blocked is True

    def test_end_work_block_sets_block_reason(self, engine: KanbanEngine) -> None:
        """end_work(block) sets block_reason to the provided value."""
        task = engine.create_task("Block reason task", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Blocking", outcome="block", block_reason="need more info"
        )
        record = engine.show_task(str(task.id))
        assert record.block_reason == "need more info"

    def test_end_work_block_releases_claimed_by(self, engine: KanbanEngine) -> None:
        """end_work(block) clears claimed_by."""
        task = engine.create_task("Release on block", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Releasing", outcome="block", block_reason="stuck")
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None

    def test_end_work_block_releases_claimed_at(self, engine: KanbanEngine) -> None:
        """end_work(block) clears claimed_at."""
        task = engine.create_task("Release at on block", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Releasing", outcome="block", block_reason="stuck")
        record = engine.show_task(str(task.id))
        assert record.claimed_at is None


# ===========================================================================
# TestFromAC_EndWorkReject — AC6
# ===========================================================================


class TestFromAC_EndWorkReject:
    """Tests for AC6: end_work(reject) appends note, moves to specified status, releases claim."""

    def test_end_work_reject_appends_note(self, engine: KanbanEngine) -> None:
        """Note is appended to task body after end_work(reject)."""
        task = engine.create_task("Reject note task", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Needs rework", outcome="reject", move_to="research"
        )
        record = engine.show_task(str(task.id))
        assert "Needs rework" in record.body

    def test_end_work_reject_moves_to_specified_status(self, engine: KanbanEngine) -> None:
        """end_work(reject) sets task status to the move_to parameter value."""
        task = engine.create_task("Moving task", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Back to backlog", outcome="reject", move_to="backlog"
        )
        record = engine.show_task(str(task.id))
        assert record.status == "backlog"

    def test_end_work_reject_to_research_default(self, engine: KanbanEngine) -> None:
        """end_work(reject) with no move_to defaults to 'research' status."""
        task = engine.create_task("Default reject", status="in-progress")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Default move", outcome="reject")
        record = engine.show_task(str(task.id))
        assert record.status == "research"

    def test_end_work_reject_releases_claimed_by(self, engine: KanbanEngine) -> None:
        """end_work(reject) clears claimed_by."""
        task = engine.create_task("Release on reject", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Rejecting", outcome="reject", move_to="research"
        )
        record = engine.show_task(str(task.id))
        assert record.claimed_by is None

    def test_end_work_reject_releases_claimed_at(self, engine: KanbanEngine) -> None:
        """end_work(reject) clears claimed_at."""
        task = engine.create_task("Release at on reject", status="todo")
        engine.start_work(str(task.id))
        engine.end_work(
            str(task.id), note="Rejecting", outcome="reject", move_to="research"
        )
        record = engine.show_task(str(task.id))
        assert record.claimed_at is None

    def test_end_work_reject_returns_updated_status(self, engine: KanbanEngine) -> None:
        """end_work(reject) returns a TaskRecord with the rejected-to status."""
        task = engine.create_task("Return on reject", status="in-progress")
        engine.start_work(str(task.id))
        result = engine.end_work(
            str(task.id), note="Rejected", outcome="reject", move_to="research"
        )
        assert result.id == task.id
        assert result.status == "research"


# ===========================================================================
# TestFromAC_EndWorkBlockGuard — AC7
# ===========================================================================


class TestFromAC_EndWorkBlockGuard:
    """Tests for AC7: end_work with outcome=block but empty block_reason raises."""

    def test_end_work_block_empty_reason_raises(self, engine: KanbanEngine) -> None:
        """end_work(block) with block_reason='' raises ValueError."""
        task = engine.create_task("Block guard test", status="in-progress")
        engine.start_work(str(task.id))
        with pytest.raises(ValueError, match="block_reason"):  # noqa: PT011
            engine.end_work(
                str(task.id), note="Blocking", outcome="block", block_reason=""
            )

    def test_end_work_block_missing_reason_does_not_set_blocked(
        self, engine: KanbanEngine
    ) -> None:
        """On missing block_reason, blocked flag remains False — no partial mutation."""
        task = engine.create_task("Guard no modify", status="in-progress")
        engine.start_work(str(task.id))
        with pytest.raises(ValueError):  # noqa: PT011
            engine.end_work(
                str(task.id), note="Block attempt", outcome="block", block_reason=""
            )
        record = engine.show_task(str(task.id))
        assert record.blocked is False

    def test_end_work_block_with_nonempty_reason_does_not_raise(
        self, engine: KanbanEngine
    ) -> None:
        """end_work(block) with a non-empty block_reason does not raise."""
        task = engine.create_task("Block with reason", status="in-progress")
        engine.start_work(str(task.id))
        # Must not raise when block_reason is provided
        engine.end_work(
            str(task.id), note="Blocking now", outcome="block", block_reason="real reason"
        )
