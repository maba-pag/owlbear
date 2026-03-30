"""Task selector for the OwlBear dispatch planner.

Provides constants and select_tasks() for choosing which tasks to dispatch
and which agents should handle them based on pipeline status.
"""

from __future__ import annotations

from owlbear.planner.gates import check_gates
from owlbear.planner.models import DispatchEntry, DispatchPlan, Task

PRIORITY_RANK: dict[str, int] = {
    "critical": 0,
    "needed": 1,
    "important": 2,
    "nice-to-have": 3,
    "someday": 4,
}

STATUS_RANK: dict[str, int] = {
    "done": 0,
    "docs": 1,
    "review": 2,
    "in-progress": 3,
    "todo": 4,
    "backlog": 5,
    "ideation": 6,
}

STATUS_AGENT_MAP: dict[str, str] = {
    "ideation": "researcher",
    "backlog": "architect",
    "todo": "test-writer",
    "in-progress": "builder",
    "review": "reviewer",
    "docs": "writer",
    "done": "auditor",
}

DISPATCH_CAP: int = 20

_MAX_PRIORITY_RANK = max(PRIORITY_RANK.values())
_MAX_STATUS_RANK = max(STATUS_RANK.values())

_TARGET_STATUS: dict[str, str] = {
    "ideation": "backlog",
    "backlog": "todo",
    "todo": "in-progress",
    "in-progress": "review",
    "review": "docs",
    "docs": "done",
    "done": "archived",
}


def select_tasks(tasks: list[Task]) -> DispatchPlan:
    """Select dispatchable tasks and return a dispatch plan.

    Filters tasks through check_gates(), applies DECOMP routing override,
    sorts by (priority_rank, status_rank) ascending, caps at DISPATCH_CAP,
    and maps each task to the appropriate agent via STATUS_AGENT_MAP.

    Unknown priority or status keys receive a fallback rank that sorts them
    to the end of the list while still including them in the plan.
    """
    passing = [t for t in tasks if check_gates(t)]

    def _sort_key(task: Task) -> tuple[int, int]:
        prank = PRIORITY_RANK.get(task.priority, _MAX_PRIORITY_RANK + 1)
        srank = STATUS_RANK.get(task.status, _MAX_STATUS_RANK + 1)
        return (prank, srank)

    sorted_tasks = sorted(passing, key=_sort_key)[:DISPATCH_CAP]

    entries = []
    for task in sorted_tasks:
        if "Needs decomposition:" in task.body:
            agent = "kanban-planner"
        else:
            agent = STATUS_AGENT_MAP.get(task.status, "architect")
        target = _TARGET_STATUS.get(task.status, task.status)
        entries.append(
            DispatchEntry(task_id=task.id, agent=agent, target_status=target)
        )

    return DispatchPlan(entries=entries)
