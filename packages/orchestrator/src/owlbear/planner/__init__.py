"""OwlBear planner subpackage — board reader, gate checks, and dispatch planning."""

from __future__ import annotations

from owlbear.planner.board import BoardReadError, read_board
from owlbear.planner.gates import check_atomicity, check_clarity, check_gates, check_tdd
from owlbear.planner.models import DispatchEntry, DispatchPlan, Task, task_list_adapter
from owlbear.planner.selector import DISPATCH_CAP, STATUS_AGENT_MAP, select_tasks

__all__ = [
    "DISPATCH_CAP",
    "STATUS_AGENT_MAP",
    "BoardReadError",
    "DispatchEntry",
    "DispatchPlan",
    "Task",
    "check_atomicity",
    "check_clarity",
    "check_gates",
    "check_tdd",
    "read_board",
    "select_tasks",
    "task_list_adapter",
]
