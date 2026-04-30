"""Failing tests for #1198: Remove legacy compat code from MCP server.

AC line (td:1):
- Tool functions use id: StrId directly — no resolution indirection
"""

from __future__ import annotations

import inspect

from owlbear_mcp_kanban.server import edit_task, end_work, move_task, start_work


class TestFromAC_LegacyCompatRemoval:
    """AC: Tool functions use id: StrId directly — no resolution indirection (td:1)."""

    def test_move_task_uses_id_directly_no_legacy_kwargs(self) -> None:
        """move_task signature has no **legacy catch-all parameter."""
        sig = inspect.signature(move_task)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "move_task still has **legacy catch-all — should use id: StrId directly"
        )

    def test_edit_task_uses_id_directly_no_legacy_kwargs(self) -> None:
        """edit_task signature has no **legacy catch-all parameter."""
        sig = inspect.signature(edit_task)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "edit_task still has **legacy catch-all — should use id: StrId directly"
        )

    def test_start_work_uses_id_directly_no_legacy_kwargs(self) -> None:
        """start_work signature has no **legacy catch-all parameter."""
        sig = inspect.signature(start_work)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "start_work still has **legacy catch-all — should use id: StrId directly"
        )

    def test_end_work_uses_id_directly_no_legacy_kwargs(self) -> None:
        """end_work signature has no **legacy catch-all parameter."""
        sig = inspect.signature(end_work)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "end_work still has **legacy catch-all — should use id: StrId directly"
        )
