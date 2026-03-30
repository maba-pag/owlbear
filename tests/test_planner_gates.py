"""Failing tests for task #207: planner gate checker functions (TDD RED).

Covers the interface contract from AC:
  - check_atomicity(): word-boundary 'and' detection in titles
  - check_tdd(): in-progress task must have '## Test-Writer Notes' in body
  - check_clarity(): bullet/numbered AC required (ideation/backlog exempt)
  - check_gates(): composite gate — True iff all three pass

All tests FAIL in RED phase — ImportError expected until builder implements #145.
"""

from __future__ import annotations

from typing import Any

from owlbear.planner.models import Task
from owlbear.planner.gates import (  # type: ignore[import]
    check_atomicity,
    check_clarity,
    check_gates,
    check_tdd,
)

# ---------------------------------------------------------------------------
# Task builder — minimal overrides on a passing todo base fixture
# ---------------------------------------------------------------------------

_BASE: dict[str, Any] = {
    "id": 1,
    "title": "Implement feature",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
    "tags": [],
    "depends_on": [],
    "class": "standard",
    "body": "## Acceptance Criteria\n- [ ] item",
    "file": "/kanban/tasks/1-task.md",
}


def _task(**overrides: Any) -> Task:
    return Task.model_validate({**_BASE, **overrides})


# ---------------------------------------------------------------------------
# TestFromAC_CheckAtomicity
# ---------------------------------------------------------------------------


class TestFromAC_CheckAtomicity:
    """Contract tests for check_atomicity() derived from #207 AC."""

    def test_title_with_and_joining_words_returns_false(self) -> None:
        """Title containing ' and ' as a standalone word returns False."""
        task = _task(title="Implement parser and update config")
        assert check_atomicity(task) is False

    def test_title_without_and_returns_true(self) -> None:
        """Title with no standalone 'and' returns True (single responsibility)."""
        task = _task(title="Implement parser")
        assert check_atomicity(task) is True

    def test_title_with_and_inside_word_returns_true(self) -> None:
        """Title with 'and' embedded in a word (e.g. 'handler') returns True — word-boundary check."""
        task = _task(title="Implement handler logic")
        assert check_atomicity(task) is True


# ---------------------------------------------------------------------------
# TestFromAC_CheckTDD
# ---------------------------------------------------------------------------


class TestFromAC_CheckTDD:
    """Contract tests for check_tdd() derived from #207 AC."""

    def test_in_progress_with_tdd_notes_returns_true(self) -> None:
        """in-progress task whose body contains '## Test-Writer Notes' returns True."""
        task = _task(status="in-progress", body="## Test-Writer Notes\n- 5 tests written")
        assert check_tdd(task) is True

    def test_in_progress_without_tdd_notes_returns_false(self) -> None:
        """in-progress task whose body lacks '## Test-Writer Notes' returns False."""
        task = _task(status="in-progress", body="## Builder Notes\n- implementation")
        assert check_tdd(task) is False

    def test_in_progress_empty_body_returns_false(self) -> None:
        """in-progress task with empty body returns False (no TW notes present)."""
        task = _task(status="in-progress", body="")
        assert check_tdd(task) is False

    def test_todo_task_always_returns_true(self) -> None:
        """Non-in-progress task (todo) returns True even with empty body."""
        task = _task(status="todo", body="")
        assert check_tdd(task) is True

    def test_review_task_always_returns_true(self) -> None:
        """Non-in-progress task (review) returns True regardless of body content."""
        task = _task(status="review", body="")
        assert check_tdd(task) is True

    def test_done_task_always_returns_true(self) -> None:
        """Non-in-progress task (done) returns True regardless of body content."""
        task = _task(status="done", body="")
        assert check_tdd(task) is True


# ---------------------------------------------------------------------------
# TestFromAC_CheckClarity
# ---------------------------------------------------------------------------


class TestFromAC_CheckClarity:
    """Contract tests for check_clarity() derived from #207 AC."""

    def test_todo_with_bullet_ac_returns_true(self) -> None:
        """todo task whose body contains a bullet item ('- item') returns True."""
        task = _task(status="todo", body="## Acceptance Criteria\n- [ ] do the thing")
        assert check_clarity(task) is True

    def test_todo_with_numbered_ac_returns_true(self) -> None:
        """todo task whose body contains a numbered item ('1. item') returns True."""
        task = _task(status="todo", body="## Acceptance Criteria\n1. first item")
        assert check_clarity(task) is True

    def test_todo_with_no_bullets_returns_false(self) -> None:
        """todo task with prose only (no bullet or numbered AC) returns False."""
        task = _task(status="todo", body="Just some prose, no list items here")
        assert check_clarity(task) is False

    def test_todo_with_empty_body_returns_false(self) -> None:
        """todo task with completely empty body returns False."""
        task = _task(status="todo", body="")
        assert check_clarity(task) is False

    def test_ideation_with_no_ac_returns_true(self) -> None:
        """ideation task with no AC is exempt from clarity gate — returns True."""
        task = _task(status="ideation", body="")
        assert check_clarity(task) is True

    def test_backlog_with_no_ac_returns_true(self) -> None:
        """backlog task with no AC is exempt from clarity gate — returns True."""
        task = _task(status="backlog", body="")
        assert check_clarity(task) is True


# ---------------------------------------------------------------------------
# TestFromAC_CheckGates
# ---------------------------------------------------------------------------


class TestFromAC_CheckGates:
    """Contract tests for check_gates() derived from #207 AC."""

    def test_task_passing_all_three_gates_returns_true(self) -> None:
        """Task passing atomicity, TDD, and clarity gates returns True."""
        task = _task(
            title="Implement feature",
            status="todo",
            body="## Acceptance Criteria\n- [ ] do the thing",
        )
        assert check_gates(task) is True

    def test_task_failing_atomicity_returns_false(self) -> None:
        """Task failing Gate 3 (title contains ' and ') returns False."""
        task = _task(
            title="Implement parser and update config",
            status="todo",
            body="## Acceptance Criteria\n- [ ] do the thing",
        )
        assert check_gates(task) is False

    def test_task_failing_tdd_returns_false(self) -> None:
        """Task failing Gate 4 (in-progress without TW notes) returns False."""
        task = _task(
            title="Implement feature",
            status="in-progress",
            body="## Builder Notes\n- working on it",
        )
        assert check_gates(task) is False

    def test_task_failing_clarity_returns_false(self) -> None:
        """Task failing Gate 5 (todo with no AC bullets) returns False."""
        task = _task(
            title="Implement feature",
            status="todo",
            body="Just prose, no acceptance criteria",
        )
        assert check_gates(task) is False
