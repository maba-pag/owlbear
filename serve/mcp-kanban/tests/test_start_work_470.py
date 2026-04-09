"""Tests for task #470: start_work compound tool.

Contract tests derived from AC:
  - start_work(task_id) exists in server.py as an MCP tool
  - Checks blocked status before proceeding (blocked guard)
  - Always auto-generates claim name via `kanban-md agent-name`
  - Claims the task at its current status (no status change) via `edit --claim`
  - Returns KanbanTask: full task details from show --json (validated)
  - Compound: replaces show + agent-name + claim + show (4 calls -> 1 tool invocation)
  - Already-claimed error propagates; agent-name failure propagates; show failure propagates
  - All errors raise ToolError (MCP isError: true)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# Import target — will raise ImportError until builder implements #470 (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_kanban.models import KanbanTask
from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    start_work,
)


# ---------------------------------------------------------------------------
# Helpers (mirroring conventions in test_server.py)
# ---------------------------------------------------------------------------


def _make_app_context(
    kanban_bin: Path = Path("/fake/kanban-md"),
    kanban_dir: Path = Path("/fake/kanban"),
) -> AppContext:
    return AppContext(kanban_bin=kanban_bin, kanban_dir=kanban_dir)


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_context()
    return ctx


_FAKE_TASK_JSON = json.dumps(
    {
        "id": 42,
        "title": "Some task",
        "status": "todo",
        "priority": "important",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
    }
)

_FAKE_BLOCKED_TASK_JSON = json.dumps(
    {
        "id": 42,
        "title": "Some task",
        "status": "todo",
        "priority": "important",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "blocked": True,
        "block_reason": "waiting on dependency",
    }
)


# ---------------------------------------------------------------------------
# TestFromAC_StartWork
# ---------------------------------------------------------------------------


class TestFromAC_StartWork:
    """Contract tests for the start_work MCP tool derived from #470 AC."""

    # ------------------------------------------------------------------ happy: auto-generated claim
    @pytest.mark.asyncio
    async def test_calls_agent_name_after_blocked_guard(self) -> None:
        """start_work calls show (blocked guard) then `agent-name` as the second subprocess call."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),  # show (blocked guard)
                ("cedar-cloud\n", "", 0),  # agent-name
                ("ok", "", 0),  # edit --claim
                (_FAKE_TASK_JSON, "", 0),  # show --json (final)
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        first_call_args: tuple[Any, ...] = mock_run.call_args_list[0][0]
        assert "show" in first_call_args
        second_call_args: tuple[Any, ...] = mock_run.call_args_list[1][0]
        assert "agent-name" in second_call_args

    @pytest.mark.asyncio
    async def test_uses_generated_name_to_claim(self) -> None:
        """start_work uses the agent-name output as the --claim value for edit."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),
                ("cedar-cloud\n", "", 0),
                ("ok", "", 0),
                (_FAKE_TASK_JSON, "", 0),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        edit_call_args: tuple[Any, ...] = mock_run.call_args_list[2][0]
        assert "--claim" in edit_call_args
        claim_idx = list(edit_call_args).index("--claim")
        assert edit_call_args[claim_idx + 1] == "cedar-cloud"

    @pytest.mark.asyncio
    async def test_calls_show_json_after_edit(self) -> None:
        """start_work calls show --json for task_id after claiming."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),
                ("cedar-cloud\n", "", 0),
                ("ok", "", 0),
                (_FAKE_TASK_JSON, "", 0),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        show_call_args: tuple[Any, ...] = mock_run.call_args_list[3][0]
        assert "show" in show_call_args
        assert "42" in show_call_args
        assert "--json" in show_call_args

    @pytest.mark.asyncio
    async def test_response_includes_task_details(self) -> None:
        """start_work response is a KanbanTask preserving full task details."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),
                ("cedar-cloud\n", "", 0),
                ("ok", "", 0),
                (_FAKE_TASK_JSON, "", 0),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42")

        assert isinstance(result, KanbanTask)
        assert result.id == 42
        assert result.title == "Some task"
        assert result.status == "todo"

    # ------------------------------------------------------------------ boundary: call count
    @pytest.mark.asyncio
    async def test_makes_exactly_four_subprocess_calls(self) -> None:
        """start_work makes exactly 4 _run_kanban calls (show guard + agent-name + edit + show)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),
                ("cedar-cloud\n", "", 0),
                ("ok", "", 0),
                (_FAKE_TASK_JSON, "", 0),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        assert mock_run.call_count == 4

    @pytest.mark.asyncio
    async def test_edit_call_does_not_include_status_flag(self) -> None:
        """start_work edit call must NOT include --status — no status change."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),
                ("cedar-cloud\n", "", 0),
                ("ok", "", 0),
                (_FAKE_TASK_JSON, "", 0),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        edit_call_args: tuple[Any, ...] = mock_run.call_args_list[2][0]
        assert "--status" not in edit_call_args
        assert "move" not in edit_call_args

    # ------------------------------------------------------------------ error: already claimed
    @pytest.mark.asyncio
    async def test_already_claimed_edit_error_raises_tool_error(self) -> None:
        """start_work raises ToolError when edit --claim returns non-zero (already claimed)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),  # show (blocked guard) ok
                ("cedar-cloud\n", "", 0),  # agent-name ok
                ("", "task is already claimed by other-agent", 1),  # edit fails
            ]
        )
        with (
            patch("owlbear_mcp_kanban.server._run_kanban", mock_run),
            pytest.raises(ToolError, match="already claimed"),
        ):
            await start_work(mcp_ctx, task_id="42")

    @pytest.mark.asyncio
    async def test_already_claimed_does_not_call_final_show(self) -> None:
        """start_work does not call final show when edit --claim fails."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),
                ("cedar-cloud\n", "", 0),
                ("", "task is already claimed", 1),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run), pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="42")

        # show (guard) + agent-name + edit only; no final show call
        assert mock_run.call_count == 3

    # ------------------------------------------------------------------ error: agent-name failure
    @pytest.mark.asyncio
    async def test_agent_name_failure_raises_tool_error(self) -> None:
        """start_work raises ToolError when agent-name subprocess fails (rc!=0)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),  # show (blocked guard) ok
                ("", "binary not found", 1),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run), pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="42")

    @pytest.mark.asyncio
    async def test_agent_name_failure_does_not_proceed_to_edit(self) -> None:
        """start_work does not call edit when agent-name fails."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),  # show (blocked guard) ok
                ("", "binary not found", 1),
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run), pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="42")

        assert mock_run.call_count == 2

    # ------------------------------------------------------------------ error: show failure
    @pytest.mark.asyncio
    async def test_show_failure_after_claim_raises_tool_error(self) -> None:
        """start_work raises ToolError when show --json fails after a successful claim."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_TASK_JSON, "", 0),  # show (blocked guard) ok
                ("cedar-cloud\n", "", 0),  # agent-name ok
                ("ok", "", 0),  # edit --claim succeeded
                ("", "task not found", 1),  # final show failed
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run), pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="42")

    # ------------------------------------------------------------------ blocked guard
    @pytest.mark.asyncio
    async def test_blocked_task_raises_tool_error(self) -> None:
        """start_work raises ToolError if the task is blocked."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                (_FAKE_BLOCKED_TASK_JSON, "", 0),  # show (blocked guard) — task is blocked
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run), pytest.raises(ToolError, match="blocked"):
            await start_work(mcp_ctx, task_id="42")

        # Only the blocked guard show call — no further calls
        assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_blocked_guard_show_failure_raises_tool_error(self) -> None:
        """start_work raises ToolError if the blocked guard show call fails."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(
            side_effect=[
                ("", "task not found", 1),  # show (blocked guard) fails
            ]
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run), pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="42")

        assert mock_run.call_count == 1
