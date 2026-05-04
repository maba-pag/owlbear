"""RED-phase tests for task #1336: Fix end_work success path.

AC coverage:
  AC1 — KanbanEngine.end_work(outcome="success") derives next status from config.statuses;
        no explicit move_to required.
  AC2 — Raw success no longer moves tasks to "research" by default (negative assertion).
  AC3 — Success from terminal status archives with archival_reason="completed",
        archival_refs=[], task moved to archive/.
  AC4 — reject without explicit move_to leaves status unchanged (not "research").

FAIL reasons:
  AC1 tests FAIL: engine default move_to="research" causes success to move backward.
  AC2 test FAILS: end_work(success) returns status="research" with the buggy default.
  AC3 tests FAIL: terminal success sets status="research" (not archived) with current code.
  AC4 test FAILS: reject without move_to moves to "research" instead of leaving unchanged.
"""

from __future__ import annotations

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Board / task helpers (matching conventions in adjacent test files)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map:
        research: researcher
        backlog: architect
        todo: test-writer
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_TASK_TMPL = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: "2026-04-25T08:00:00+00:00"
archival_reason: null
archival_refs: []
---
Task body.
"""

_UNCLAIMED_TASK_TMPL = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Task body.
"""


def _make_board(base_dir, config_yaml: str = _BASE_CONFIG):
    """Create a minimal board with config. Returns kanban_dir Path."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(kanban_dir, task_id: int = 1, status: str = "todo") -> None:
    """Write a claimed task file into the board's tasks directory."""
    content = _TASK_TMPL.format(task_id=task_id, status=status)
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")


def _make_engine(base_dir, config_yaml: str = _BASE_CONFIG) -> KanbanEngine:
    """Create a KanbanEngine backed by a fresh board in base_dir."""
    kanban_dir = _make_board(base_dir, config_yaml)
    return KanbanEngine(kanban_dir, activity_log=False)


# ---------------------------------------------------------------------------
# TestFromAC_SuccessStatusAdvancement — AC1: success derives next from sequence
# ---------------------------------------------------------------------------


class TestFromAC_SuccessStatusAdvancement:
    """end_work(outcome="success") must advance to statuses[idx+1], not to "research"."""

    def test_success_from_todo_advances_to_in_progress(self, tmp_path) -> None:
        """AC1: success from 'todo' (idx=2) advances to 'in-progress' (idx=3).

        FAIL reason: engine defaults move_to="research"; end_work sets
        status to "research" instead of computing the next status in sequence.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="todo")

        result = engine.end_work("1", note="done", outcome="success")

        assert result.status == "in-progress", (
            f"AC1: success from 'todo' must advance to 'in-progress'; "
            f"got {result.status!r}"
        )

    def test_success_from_research_advances_to_backlog(self, tmp_path) -> None:
        """AC1: success from 'research' (idx=0) advances to 'backlog' (idx=1).

        FAIL reason: engine defaults move_to="research"; status stays "research"
        instead of advancing to "backlog".
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="research")

        result = engine.end_work("1", note="done", outcome="success")

        assert result.status == "backlog", (
            f"AC1: success from 'research' must advance to 'backlog'; "
            f"got {result.status!r}"
        )

    def test_success_from_review_advances_to_done(self, tmp_path) -> None:
        """AC1: success from 'review' (idx=4) advances to 'done' (idx=5).

        FAIL reason: engine defaults move_to="research"; status moves to
        "research" instead of advancing to the next status "done".
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="review")

        result = engine.end_work("1", note="done", outcome="success")

        assert result.status == "done", (
            f"AC1: success from 'review' must advance to 'done'; got {result.status!r}"
        )

    def test_success_advances_across_all_non_terminal_steps(self, tmp_path) -> None:
        """AC1: each step in sequence advances exactly one position forward.

        Verifies that the full pipeline sequence is covered, not just one step.

        FAIL reason: current default move_to="research" always returns "research"
        regardless of starting status; all steps fail the assertion.
        """
        statuses = ["research", "backlog", "todo", "in-progress", "review"]
        expected_next = ["backlog", "todo", "in-progress", "review", "done"]

        for start, expected in zip(statuses, expected_next, strict=False):
            engine = _make_engine(tmp_path / start)
            _write_task(engine._kanban_dir, task_id=1, status=start)

            result = engine.end_work("1", note="advancing", outcome="success")

            assert result.status == expected, (
                f"AC1: success from {start!r} must advance to {expected!r}; "
                f"got {result.status!r}"
            )


# ---------------------------------------------------------------------------
# TestFromAC_SuccessAtTerminalStatus — AC3: terminal success archives the task
# ---------------------------------------------------------------------------


class TestFromAC_SuccessAtTerminalStatus:
    """end_work(outcome="success") from terminal status archives with archival_reason="completed".

    FAIL reasons (current code): engine defaults move_to="research"; _apply_outcome sets
    record.status="research" instead of triggering the archive branch, so:
    - result.archival_reason is None (not "completed")
    - result.status is "research" (not "archived")
    - the file stays in tasks/ (not moved to archive/)
    """

    def test_success_at_terminal_returns_archival_reason_completed(self, tmp_path) -> None:
        """AC3: success from 'done' sets archival_reason='completed' on the returned task.

        FAIL reason: current code sets status to 'research' (buggy default move_to);
        _apply_outcome never reaches the archive branch, so archival_reason stays None.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="done")

        result = engine.end_work("1", note="shipped", outcome="success")

        assert result.archival_reason == "completed", (
            f"AC3: success at terminal must set archival_reason='completed'; "
            f"got {result.archival_reason!r}"
        )

    def test_success_at_terminal_returns_status_archived(self, tmp_path) -> None:
        """AC3: success from 'done' sets status='archived' on the returned task.

        FAIL reason: current code sets status to 'research' (buggy default move_to);
        the archive branch is never triggered.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="done")

        result = engine.end_work("1", note="shipped", outcome="success")

        assert result.status == "archived", (
            f"AC3: success at terminal must return status='archived'; "
            f"got {result.status!r}"
        )

    def test_success_at_terminal_moves_file_to_archive_dir(self, tmp_path) -> None:
        """AC3: success from 'done' moves the task file from tasks/ to archive/.

        FAIL reason: current code sets status to 'research' without archiving;
        the file stays in tasks/ and archive/ remains empty.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="done")

        engine.end_work("1", note="shipped", outcome="success")

        archive_file = engine._archive_dir / "1-task.md"
        tasks_file = engine._tasks_dir / "1-task.md"
        assert archive_file.exists(), (
            "AC3: success at terminal must move task to archive/; file not found there"
        )
        assert not tasks_file.exists(), (
            "AC3: success at terminal must remove task from tasks/; file still present"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SuccessFromInProgress — additional AC1 step coverage
# ---------------------------------------------------------------------------


class TestFromAC_SuccessFromInProgress:
    """AC1: success from 'in-progress' must advance to 'review', not 'research'."""

    def test_success_from_in_progress_advances_to_review(self, tmp_path) -> None:
        """AC1: success from 'in-progress' (idx=3) advances to 'review' (idx=4).

        FAIL reason: engine defaults move_to='research'; status moves to 'research'
        instead of advancing to 'review'.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="in-progress")

        result = engine.end_work("1", note="shipped", outcome="success")

        assert result.status == "review", (
            f"AC1: success from 'in-progress' must advance to 'review'; "
            f"got {result.status!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_NoDefaultResearch — AC2: raw success must not default to "research"
# ---------------------------------------------------------------------------


class TestFromAC_NoDefaultResearch:
    """AC2: end_work(outcome="success") must not move any task to "research" by default."""

    def test_success_result_is_not_research(self, tmp_path) -> None:
        """AC2: success from 'todo' must NOT return status='research'.

        FAIL reason: current engine default is move_to="research"; the result status
        is always "research" regardless of the task's position in the pipeline.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="todo")

        result = engine.end_work("1", note="done", outcome="success")

        assert result.status != "research", (
            f"AC2: success must not default to 'research'; "
            f"got {result.status!r} — engine move_to default is still 'research'"
        )


# ---------------------------------------------------------------------------
# TestFromAC_RejectWithoutMoveToContract — AC4: reject default now None
# ---------------------------------------------------------------------------


class TestFromAC_RejectWithoutMoveToContract:
    """AC4: reject without explicit move_to leaves status unchanged after fix.

    Before fix: engine default move_to="research" causes reject to always set
    status="research" even without an explicit target.
    After fix: move_to=None means reject with no explicit move_to leaves status unchanged.
    """

    def test_reject_without_move_to_does_not_go_to_research(self, tmp_path) -> None:
        """AC4: reject from 'todo' without explicit move_to must not set status='research'.

        FAIL reason: current engine default move_to="research" causes _apply_outcome
        to set record.status="research" for reject (move_to is not None → sets status).
        After fix: move_to=None → status unchanged → remains 'todo'.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="todo")

        result = engine.end_work("1", note="not ready", outcome="reject")

        assert result.status != "research", (
            f"AC4: reject without explicit move_to must not go to 'research'; "
            f"got {result.status!r} — engine move_to default is still 'research'"
        )
