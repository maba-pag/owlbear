"""Failing tests for task #207: planner task selector (TDD RED).

Covers the interface contract from AC:
  - PRIORITY_RANK: all 5 priorities, correct ordering (critical=0 to someday=4)
  - STATUS_RANK: all 7 statuses, correct ordering (done=0 to research=6)
  - STATUS_AGENT_MAP: all 7 statuses mapped to correct pipeline agent names
  - DISPATCH_CAP: value is 20
  - select_tasks(): empty input, single task, gate exclusion, sorting,
    dispatch cap, DECOMP override, unknown priority/status fallback

All tests FAIL in RED phase — ImportError expected until builder implements #145.
"""

from __future__ import annotations

from typing import Any

from owlbear.planner.models import DispatchEntry, DispatchPlan, Task
from owlbear.planner.selector import (  # type: ignore[import]
    DISPATCH_CAP,
    PRIORITY_RANK,
    STATUS_AGENT_MAP,
    STATUS_RANK,
    select_tasks,
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
# TestFromAC_Constants
# ---------------------------------------------------------------------------


class TestFromAC_Constants:
    """Contract tests for selector module constants derived from #207 AC."""

    def test_priority_rank_contains_all_five_priorities(self) -> None:
        """PRIORITY_RANK has exactly the 5 canonical priority names."""
        assert set(PRIORITY_RANK.keys()) == {
            "critical",
            "needed",
            "important",
            "nice-to-have",
            "someday",
        }

    def test_priority_rank_correct_ordering(self) -> None:
        """PRIORITY_RANK: critical=0, needed=1, important=2, nice-to-have=3, someday=4."""
        assert PRIORITY_RANK["critical"] == 0
        assert PRIORITY_RANK["needed"] == 1
        assert PRIORITY_RANK["important"] == 2
        assert PRIORITY_RANK["nice-to-have"] == 3
        assert PRIORITY_RANK["someday"] == 4

    def test_status_rank_contains_all_seven_statuses(self) -> None:
        """STATUS_RANK has exactly the 7 canonical pipeline statuses."""
        assert set(STATUS_RANK.keys()) == {
            "done",
            "docs",
            "review",
            "in-progress",
            "todo",
            "backlog",
            "research",
        }

    def test_status_rank_correct_ordering(self) -> None:
        """STATUS_RANK: done=0, docs=1, review=2, in-progress=3, todo=4, backlog=5, research=6."""
        assert STATUS_RANK["done"] == 0
        assert STATUS_RANK["docs"] == 1
        assert STATUS_RANK["review"] == 2
        assert STATUS_RANK["in-progress"] == 3
        assert STATUS_RANK["todo"] == 4
        assert STATUS_RANK["backlog"] == 5
        assert STATUS_RANK["research"] == 6

    def test_status_agent_map_has_all_seven_statuses(self) -> None:
        """STATUS_AGENT_MAP contains all 7 pipeline statuses."""
        assert set(STATUS_AGENT_MAP.keys()) == {
            "research",
            "backlog",
            "todo",
            "in-progress",
            "review",
            "docs",
            "done",
        }

    def test_status_agent_map_correct_agents(self) -> None:
        """STATUS_AGENT_MAP maps each status to the correct pipeline agent."""
        assert STATUS_AGENT_MAP["research"] == "researcher"
        assert STATUS_AGENT_MAP["backlog"] == "architect"
        assert STATUS_AGENT_MAP["todo"] == "test-writer"
        assert STATUS_AGENT_MAP["in-progress"] == "builder"
        assert STATUS_AGENT_MAP["review"] == "reviewer"
        assert STATUS_AGENT_MAP["docs"] == "writer"
        assert STATUS_AGENT_MAP["done"] == "auditor"

    def test_dispatch_cap_is_twenty(self) -> None:
        """DISPATCH_CAP equals 20."""
        assert DISPATCH_CAP == 20


# ---------------------------------------------------------------------------
# TestFromAC_SelectTasks
# ---------------------------------------------------------------------------


class TestFromAC_SelectTasks:
    """Contract tests for select_tasks() derived from #207 AC."""

    def test_empty_input_returns_empty_dispatch_plan(self) -> None:
        """select_tasks([]) returns DispatchPlan with empty entries list."""
        result = select_tasks([])
        assert isinstance(result, DispatchPlan)
        assert result.entries == []

    def test_single_passing_task_produces_correct_dispatch_entry(self) -> None:
        """Single gate-passing todo task produces DispatchEntry with correct agent and target."""
        task = _task(
            id=42,
            status="todo",
            title="Implement feature",
            body="## Acceptance Criteria\n- [ ] item",
        )
        result = select_tasks([task])
        assert len(result.entries) == 1
        entry = result.entries[0]
        assert isinstance(entry, DispatchEntry)
        assert entry.task_id == 42
        assert entry.agent == "test-writer"
        assert entry.target_status == "in-progress"

    def test_gate_failing_task_is_excluded(self) -> None:
        """todo task with no AC bullets (fails clarity gate) is excluded from output."""
        task = _task(
            id=10,
            status="todo",
            title="Implement feature",
            body="",
        )
        result = select_tasks([task])
        assert result.entries == []

    def test_tasks_sorted_by_priority_then_pipeline_proximity(self) -> None:
        """critical+done sorts before needed+backlog (priority rank, then status rank)."""
        needed_backlog = _task(
            id=1,
            status="backlog",
            priority="needed",
            title="Needed backlog task",
            body="",  # backlog is exempt from clarity gate
        )
        critical_done = _task(
            id=2,
            status="done",
            priority="critical",
            title="Critical done task",
            body="- [ ] item",  # has bullet in case clarity applies to done
        )
        result = select_tasks([needed_backlog, critical_done])
        assert len(result.entries) == 2
        assert result.entries[0].task_id == 2  # critical+done first
        assert result.entries[1].task_id == 1  # needed+backlog second

    def test_twenty_five_tasks_capped_at_twenty(self) -> None:
        """25 gate-passing tasks produce at most DISPATCH_CAP (20) entries."""
        tasks = [
            _task(
                id=i,
                title=f"Task {i}",
                status="todo",
                body="## Acceptance Criteria\n- [ ] item",
            )
            for i in range(1, 26)
        ]
        result = select_tasks(tasks)
        assert len(result.entries) <= DISPATCH_CAP

    def test_decomp_override_maps_to_kanban_planner(self) -> None:
        """Task with 'Needs decomposition:' in body dispatches to 'kanban-planner' agent."""
        task = _task(
            id=99,
            status="todo",
            title="Implement large feature",
            body="## Acceptance Criteria\n- [ ] item\nNeeds decomposition: scope too large",
        )
        result = select_tasks([task])
        assert len(result.entries) == 1
        assert result.entries[0].agent == "planner"

    def test_unknown_priority_uses_fallback_rank_sorts_to_end(self) -> None:
        """Task with unknown priority is not excluded — sorts after known priorities."""
        critical_task = _task(
            id=1,
            status="todo",
            priority="critical",
            title="Critical task",
            body="## Acceptance Criteria\n- [ ] item",
        )
        unknown_priority_task = _task(
            id=2,
            status="todo",
            priority="unknown-xyz",
            title="Unknown priority task",
            body="## Acceptance Criteria\n- [ ] item",
        )
        result = select_tasks([unknown_priority_task, critical_task])
        task_ids = [e.task_id for e in result.entries]
        assert 1 in task_ids, "known-priority task must be included"
        assert 2 in task_ids, "unknown-priority task must not be excluded"
        assert task_ids.index(1) < task_ids.index(2), "critical sorts before unknown"

    def test_unknown_status_uses_fallback_rank_sorts_to_end(self) -> None:
        """Task with unknown status is not excluded — sorts after known statuses."""
        done_task = _task(
            id=1,
            status="done",
            priority="important",
            title="Done task",
            body="- [ ] item",
        )
        unknown_status_task = _task(
            id=2,
            status="unknown-xyz",
            priority="important",
            title="Unknown status task",
            body="## Acceptance Criteria\n- [ ] item",
        )
        result = select_tasks([unknown_status_task, done_task])
        task_ids = [e.task_id for e in result.entries]
        assert 1 in task_ids, "known-status task must be included"
        assert 2 in task_ids, "unknown-status task must not be excluded"
        assert task_ids.index(1) < task_ids.index(2), "done sorts before unknown"
