"""OwlBear planner subpackage — board reader, gate checks, and dispatch planning.

Dual-path architecture (#619):

- In-process path: loop.py and cli.py import directly from this package for
  headless ACP dispatch (no MCP server required).
- MCP path: VS Code agents call the ``pick_tasks`` tool in the owlbear-kanban
  MCP server (serve/mcp-kanban), which replicates the gate/sort logic inline.

Both paths stay in sync manually — gate logic changes must be applied to both
gates.py here *and* the inline copy in owlbear_mcp_kanban/server.py.
"""

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
