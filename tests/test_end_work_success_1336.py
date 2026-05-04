"""RED-phase tests for task #1336: Fix end_work success path.

AC coverage:
  AC1 — end_work(outcome="success") derives next status from config.statuses[idx+1],
        not from move_to default "research"
  AC2 — end_work(outcome="success") at last configured status raises a clear error
        (cannot advance past final status)
  AC3 — end_work(outcome="reject", move_to=X) still uses explicit move_to (regression guard)

FAIL reasons:
  AC1 tests FAIL: engine default move_to="research" causes success to move backward.
  AC2 tests FAIL: engine moves to "research" instead of raising an error at terminal.
  AC3 tests PASS in RED (reject already works); included as regression guards per skill rules.
"""

from __future__ import annotations

import pytest

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
# TestFromAC_SuccessAtTerminalStatus — AC2: raise error at final status
# ---------------------------------------------------------------------------


class TestFromAC_SuccessAtTerminalStatus:
    """end_work(outcome="success") at the last configured status must raise a clear error."""

    def test_success_at_last_config_status_raises_error(self, tmp_path) -> None:
        """AC2: success from 'done' (last in statuses) raises a ValueError.

        FAIL reason: current code moves status to "research" (the move_to default)
        without raising any error; no exception is thrown.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="done")

        with pytest.raises((ValueError, Exception)) as exc_info:
            engine.end_work("1", note="what next?", outcome="success")

        assert exc_info is not None, (
            "AC2: success at terminal status 'done' must raise an error; "
            "no exception was raised"
        )

    def test_success_at_terminal_error_message_mentions_advance(self, tmp_path) -> None:
        """AC2: error raised at last status describes the 'cannot advance' constraint.

        FAIL reason: no error is raised at all; the task moves to "research" silently.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="done")

        with pytest.raises((ValueError, Exception)) as exc_info:
            engine.end_work("1", note="stuck", outcome="success")

        error_text = str(exc_info.value).lower()
        assert any(
            kw in error_text for kw in ("advance", "final", "terminal", "last", "end")
        ), (
            f"AC2: error message must describe inability to advance past final status; "
            f"got: {str(exc_info.value)!r}"
        )

    def test_success_at_terminal_raises_not_moves_backward(self, tmp_path) -> None:
        """AC2: success at terminal must raise an error, not silently move to 'research'.

        A correctly implemented engine raises a clear error at the last status.
        The buggy engine moves to 'research' with no error.

        FAIL reason: DID NOT RAISE — end_work sets status='research' and returns
        a result instead of raising an error.
        """
        engine = _make_engine(tmp_path)
        _write_task(engine._kanban_dir, task_id=1, status="done")

        with pytest.raises(ValueError) as exc_info:
            engine.end_work("1", note="oops", outcome="success")

        # After fix: error must name the status that blocked advancement
        assert "done" in str(exc_info.value).lower() or any(
            kw in str(exc_info.value).lower()
            for kw in ("advance", "final", "terminal", "last", "beyond")
        ), (
            f"AC2: error must reference the terminal state or advancement constraint; "
            f"got: {str(exc_info.value)!r}"
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
