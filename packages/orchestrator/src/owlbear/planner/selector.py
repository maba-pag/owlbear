"""Task selector stub — full implementation in task #145."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.planner.models import DispatchPlan, Task


def select_tasks(tasks: list[Task], **kwargs: object) -> DispatchPlan:
    """Select dispatchable tasks and return a dispatch plan.

    Stub implementation — the full gate-checking and priority-ranking logic
    will be implemented in task #145.
    """
    msg = "select_tasks not yet implemented — see task #145"
    raise NotImplementedError(msg)
