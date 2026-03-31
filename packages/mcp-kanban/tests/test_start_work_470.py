"""Failing tests for task #470: start_work compound tool (TDD RED).

Contract tests derived from AC:
  - start_work(task_id, claim?) exists in server.py as an MCP tool
  - If no claim provided, auto-generate via `kanban-md agent-name`
  - Claim the task at its current status (no status change) via `edit --claim`
  - Return JSON: full task details (like show_task) + injected `claim_name` field
  - Compound: replaces claim + show (2 calls -> 1 tool invocation)
  - Already-claimed error propagates; agent-name failure propagates; show failure propagates

All tests FAIL in RED phase — start_work does not exist yet.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import target — will raise ImportError until builder implements #470 (RED)
# ---------------------------------------------------------------------------
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


_FAKE_TASK_JSON = json.dumps({
    "id": 42,
    "title": "Some task",
    "status": "todo",
    "priority": "important",
})


# ---------------------------------------------------------------------------
# TestFromAC_StartWork
# ---------------------------------------------------------------------------


class TestFromAC_StartWork:
    """Contract tests for the start_work MCP tool derived from #470 AC."""

    # ------------------------------------------------------------------ happy: explicit claim
    @pytest.mark.asyncio
    async def test_explicit_claim_calls_edit_with_claim_flag(self) -> None:
        """start_work with explicit claim calls edit --claim {claim} for the given task_id."""
        mcp_ctx = _make_mcp_ctx()
        # side_effect: call 1 = edit (returns ok), call 2 = show (returns JSON)
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        edit_call_args: tuple[Any, ...] = mock_run.call_args_list[0][0]
        assert "edit" in edit_call_args
        assert "42" in edit_call_args
        assert "--claim" in edit_call_args
        assert "builder-agent" in edit_call_args

    @pytest.mark.asyncio
    async def test_explicit_claim_calls_show_json_after_edit(self) -> None:
        """start_work with explicit claim calls show --json for task_id after claiming."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        show_call_args: tuple[Any, ...] = mock_run.call_args_list[1][0]
        assert "show" in show_call_args
        assert "42" in show_call_args
        assert "--json" in show_call_args

    @pytest.mark.asyncio
    async def test_explicit_claim_returns_json_with_claim_name_field(self) -> None:
        """start_work with explicit claim returns JSON containing a claim_name field."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        data = json.loads(result)
        assert "claim_name" in data
        assert data["claim_name"] == "builder-agent"

    @pytest.mark.asyncio
    async def test_explicit_claim_response_includes_task_details(self) -> None:
        """start_work response preserves full task details from show_task output."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        data = json.loads(result)
        # All fields from show_task output must be present
        assert data["id"] == 42
        assert data["title"] == "Some task"
        assert data["status"] == "todo"

    # ------------------------------------------------------------------ happy: auto-generated claim
    @pytest.mark.asyncio
    async def test_no_claim_calls_agent_name_first(self) -> None:
        """start_work with no claim calls `agent-name` as the first subprocess call."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("cedar-cloud\n", "", 0),   # agent-name
            ("ok", "", 0),               # edit --claim
            (_FAKE_TASK_JSON, "", 0),    # show --json
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        first_call_args: tuple[Any, ...] = mock_run.call_args_list[0][0]
        assert "agent-name" in first_call_args

    @pytest.mark.asyncio
    async def test_no_claim_uses_generated_name_to_claim(self) -> None:
        """start_work with no claim uses the agent-name output as the --claim value for edit."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("cedar-cloud\n", "", 0),
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        edit_call_args: tuple[Any, ...] = mock_run.call_args_list[1][0]
        assert "--claim" in edit_call_args
        # The generated name (stripped) appears as the claim value
        claim_idx = list(edit_call_args).index("--claim")
        assert edit_call_args[claim_idx + 1] == "cedar-cloud"

    @pytest.mark.asyncio
    async def test_no_claim_response_claim_name_matches_generated(self) -> None:
        """start_work with no claim sets claim_name in response to the generated name."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("cedar-cloud\n", "", 0),
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42")

        data = json.loads(result)
        assert data["claim_name"] == "cedar-cloud"

    # ------------------------------------------------------------------ boundary: call count
    @pytest.mark.asyncio
    async def test_explicit_claim_makes_exactly_two_subprocess_calls(self) -> None:
        """start_work with explicit claim makes exactly 2 _run_kanban calls (edit + show), not 3."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42", claim="explicit-agent")

        assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_no_claim_makes_exactly_three_subprocess_calls(self) -> None:
        """start_work with no claim makes exactly 3 _run_kanban calls (agent-name + edit + show)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("cedar-cloud\n", "", 0),
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        assert mock_run.call_count == 3

    @pytest.mark.asyncio
    async def test_edit_call_does_not_include_status_flag(self) -> None:
        """start_work edit call must NOT include --status — no status change."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        edit_call_args: tuple[Any, ...] = mock_run.call_args_list[0][0]
        assert "--status" not in edit_call_args
        assert "move" not in edit_call_args

    # ------------------------------------------------------------------ edge: empty string claim
    @pytest.mark.asyncio
    async def test_empty_string_claim_auto_generates(self) -> None:
        """start_work with claim='' (empty string) auto-generates a name via agent-name."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("misty-river\n", "", 0),
            ("ok", "", 0),
            (_FAKE_TASK_JSON, "", 0),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42", claim="")

        # Three calls made (agent-name + edit + show)
        assert mock_run.call_count == 3
        data = json.loads(result)
        assert data["claim_name"] == "misty-river"

    # ------------------------------------------------------------------ error: already claimed
    @pytest.mark.asyncio
    async def test_already_claimed_edit_error_returns_error_string(self) -> None:
        """start_work returns 'error: {stderr}' when edit --claim returns non-zero (already claimed)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("", "task is already claimed by other-agent", 1),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        assert result.startswith("error:")
        assert "already claimed" in result

    @pytest.mark.asyncio
    async def test_already_claimed_does_not_call_show(self) -> None:
        """start_work does not call show when edit --claim fails."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("", "task is already claimed", 1),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        # Only the edit call was made; no show call
        assert mock_run.call_count == 1

    # ------------------------------------------------------------------ error: agent-name failure
    @pytest.mark.asyncio
    async def test_agent_name_failure_returns_error_string(self) -> None:
        """start_work returns 'error: {stderr}' when agent-name subprocess fails (rc!=0)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("", "binary not found", 1),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42")

        assert result.startswith("error:")

    @pytest.mark.asyncio
    async def test_agent_name_failure_does_not_proceed_to_edit(self) -> None:
        """start_work does not call edit when agent-name fails."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("", "binary not found", 1),
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await start_work(mcp_ctx, task_id="42")

        # Only agent-name was called
        assert mock_run.call_count == 1

    # ------------------------------------------------------------------ error: show failure
    @pytest.mark.asyncio
    async def test_show_failure_after_claim_returns_error_string(self) -> None:
        """start_work returns 'error: {stderr}' when show --json fails after a successful claim."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(side_effect=[
            ("ok", "", 0),              # edit --claim succeeded
            ("", "task not found", 1),  # show failed
        ])
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            result = await start_work(mcp_ctx, task_id="42", claim="builder-agent")

        assert result.startswith("error:")
