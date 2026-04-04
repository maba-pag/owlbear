"""Failing tests for task #489: move/pick JSON output, drop board_context (TDD RED).

Covers the contract from AC:
  - move_task passes --json to _run_kanban (AC line 1)
  - pick_task passes --json to _run_kanban (AC line 2)
  - board_context function removed from server.py (not registered as MCP tool)
  - board_context removed from __all__
  - board_context not importable as a module-level name

Note: AC lines 1 & 2 (move/pick --json) are already covered by failing tests in
packages/mcp-kanban/tests/test_server.py (test_move_task_success_passes_args,
test_pick_task_success_passes_args). Tests here provide additional contract-level
coverage from the tool registration and module API perspective.

All tests FAIL in RED phase:
  - board_context IS currently registered as a tool
  - board_context IS currently in __all__
  - board_context IS currently defined on the server module
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import (
    AppContext,
    mcp,
    move_task,
)
import owlbear_mcp_kanban.server as server_mod


# ---------------------------------------------------------------------------
# Helpers (copied from packages/mcp-kanban/tests/test_server.py conventions)
# ---------------------------------------------------------------------------

_FAKE_TASK_JSON = json.dumps({
    "id": 1,
    "title": "Fake Task",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
    "class": "standard",
})


def _make_app_ctx() -> AppContext:
    from pathlib import Path

    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _registered_tool_names() -> set[str]:
    """Return the set of tool names currently registered on the MCP server."""
    if hasattr(mcp, "_tool_manager"):
        return {
            getattr(t, "name", None)
            for t in mcp._tool_manager.list_tools()  # noqa: SLF001
        } - {None}
    return set()


# ---------------------------------------------------------------------------
# TestFromAC_DropBoardContext
# ---------------------------------------------------------------------------


class TestFromAC_DropBoardContext:
    """Contract tests verifying board_context is removed from the mcp-kanban server."""

    # AC: board_context function and @mcp.tool() decorator removed from server.py
    def test_board_context_not_registered_as_mcp_tool(self) -> None:
        """board_context must not appear in the set of registered MCP tools after removal.

        Currently FAILS because board_context IS registered.
        """
        tool_names = _registered_tool_names()
        assert "board_context" not in tool_names, (
            f"board_context is still registered as an MCP tool; "
            f"registered tools: {tool_names!r}"
        )

    # AC: board_context removed from __all__
    def test_board_context_not_in_server_all(self) -> None:
        """board_context must not appear in server.__all__ after removal.

        Currently FAILS because board_context IS in __all__.
        """
        assert "board_context" not in server_mod.__all__, (
            "board_context is still listed in server.__all__; "
            "it must be removed along with the function definition"
        )

    # AC: board_context function removed (no module-level attribute)
    def test_board_context_not_defined_on_server_module(self) -> None:
        """board_context must not exist as a name on the server module after removal.

        Currently FAILS because the function IS defined at module level.
        """
        assert not hasattr(server_mod, "board_context"), (
            "server module still has a 'board_context' attribute; "
            "the function definition must be removed"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MovePickJsonOutput
# ---------------------------------------------------------------------------


class TestFromAC_MovePickJsonOutput:
    """Contract tests verifying move_task and pick_task pass --json to _run_kanban.

    These duplicate-guard the AC lines also covered by test_server.py, focusing
    on the JSON-output contract from the caller's perspective.
    """

    # AC: move_task passes --json to _run_kanban
    @pytest.mark.asyncio
    async def test_move_task_passes_json_flag_to_run_kanban(self) -> None:
        """move_task must include '--json' in the args tuple passed to _run_kanban.

        Currently FAILS because move_task calls _run_kanban without '--json'.
        """
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_FAKE_TASK_JSON, "", 0)),
        ) as mock_run:
            await move_task(mcp_ctx, task_id="1", status="review")

        args_used: tuple = mock_run.call_args[0]
        assert "--json" in args_used, (
            f"move_task did not pass '--json' to _run_kanban; args: {args_used!r}"
        )
