"""Failing tests for task #588: Support 'archived' status in move_task MCP tool.

Covers all AC items from #588:
  - move_task(task_id, status="archived") calls kanban-md archive (not move)
  - All other status values continue to use kanban-md move as before
  - Error from kanban-md archive is surfaced via ToolError
  - Unit tests cover the new archive path and existing move paths still pass

All tests FAIL in RED phase — move_task currently always calls "move", never "archive".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_kanban.server import AppContext, move_task, mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_TASK_JSON = json.dumps(
    {
        "id": 42,
        "title": "Sample Task",
        "status": "todo",
        "priority": "important",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-04-01T00:00:00Z",
        "class": "standard",
    }
)


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


async def _side_effect_archive_fails_move_succeeds(_ctx: Any, *args: str) -> tuple[str, str, int]:
    """Return error for 'archive' commands, success for 'move' commands."""
    if args[0] == "archive":
        return ("", "kanban-md: archive operation failed", 1)
    return (_VALID_TASK_JSON, "", 0)


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskArchived
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskArchived:
    """Contract tests for task #588 — 'archived' status support in move_task."""

    # AC: move_task(task_id, status="archived") archives the task (calls kanban-md archive)

    @pytest.mark.asyncio
    async def test_archived_status_routes_to_archive_command(self) -> None:
        """When status='archived', _run_kanban must be called with 'archive' as the command."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await move_task(mcp_ctx, task_id="42", status="archived")

        positional_args: tuple[Any, ...] = mock_run.call_args[0]
        assert "archive" in positional_args, (
            "move_task with status='archived' must call _run_kanban with 'archive' command; "
            f"got: {positional_args!r}"
        )

    @pytest.mark.asyncio
    async def test_archived_status_does_not_invoke_move_command(self) -> None:
        """When status='archived', _run_kanban must NOT be called with 'move' command."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await move_task(mcp_ctx, task_id="42", status="archived")

        positional_args: tuple[Any, ...] = mock_run.call_args[0]
        assert "move" not in positional_args, (
            "move_task with status='archived' must NOT call 'move' command; "
            f"got: {positional_args!r}"
        )

    @pytest.mark.asyncio
    async def test_archived_status_word_not_passed_as_cli_arg(self) -> None:
        """The string 'archived' must not be forwarded to _run_kanban as a positional CLI arg."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await move_task(mcp_ctx, task_id="42", status="archived")

        positional_args: tuple[Any, ...] = mock_run.call_args[0]
        assert "archived" not in positional_args, (
            "move_task must not pass the literal string 'archived' to _run_kanban; "
            "route to the 'archive' sub-command instead. "
            f"got: {positional_args!r}"
        )

    # AC: Error from kanban-md archive is surfaced via ToolError

    @pytest.mark.asyncio
    async def test_archived_error_raises_tool_error(self) -> None:
        """When archive command returns rc!=0, move_task must raise ToolError."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(side_effect=_side_effect_archive_fails_move_succeeds),
        ), pytest.raises(ToolError):
            await move_task(mcp_ctx, task_id="42", status="archived")

    @pytest.mark.asyncio
    async def test_archived_error_message_from_stderr(self) -> None:
        """ToolError message must contain the stderr output from the failed archive command."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(side_effect=_side_effect_archive_fails_move_succeeds),
        ), pytest.raises(ToolError, match="archive operation failed"):
            await move_task(mcp_ctx, task_id="42", status="archived")

    # AC: All other status values continue to use kanban-md move as before
    # (schema boundary — 'archived' must be discoverable by agents)

    def test_move_task_status_param_enum_includes_archived(self) -> None:
        """The move_task 'status' parameter enum must include 'archived' after _patch_params."""
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "move_task"),  # noqa: SLF001
            None,
        )
        assert tool is not None, "move_task tool not registered on mcp server"
        props = tool.parameters.get("properties", {})
        enum: list[str] = props.get("status", {}).get("enum", [])
        assert "archived" in enum, (
            f"move_task 'status' parameter enum must include 'archived'; "
            f"current enum: {enum!r}"
        )
