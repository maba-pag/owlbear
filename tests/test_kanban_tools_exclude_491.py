"""Failing tests for task #491: KANBAN_TOOLS_EXCLUDE in mcp-kanban server (TDD RED).

Covers the contract from AC:
  - _apply_tool_exclusions(server, ...) signature and return type
  - Calls server.remove_tool for each comma-separated name with whitespace stripped
  - Invalid/unknown tool names silently ignored (exception swallowed)
  - Default (no env var): all 7 tools registered, no removals
  - app_lifespan calls _apply_tool_exclusions before yield

All tests FAIL in RED phase — AttributeError/ImportError until builder implements #491.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import target — _apply_tool_exclusions does not exist yet (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_kanban.server import (  # type: ignore[import]
    _apply_tool_exclusions,
    app_lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_server() -> MagicMock:
    """Return a MagicMock mimicking a FastMCP server with remove_tool."""
    server = MagicMock()
    server.remove_tool = MagicMock()
    return server


# ---------------------------------------------------------------------------
# TestFromAC_ApplyToolExclusions
# ---------------------------------------------------------------------------


class TestFromAC_ApplyToolExclusions:
    """Contract tests for _apply_tool_exclusions derived from #491 AC."""

    # AC: reads KANBAN_TOOLS_EXCLUDE env var, calls server.remove_tool for each name
    def test_exclude_single_tool_calls_remove_tool_once(self) -> None:
        """Excluding one tool name causes remove_tool to be called exactly once with that name."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "list_tasks"}):
            _apply_tool_exclusions(server)

        server.remove_tool.assert_called_once_with("list_tasks")

    # AC: comma-separated list → each name gets a remove_tool call
    def test_exclude_multiple_tools_calls_remove_tool_for_each(self) -> None:
        """Excluding multiple comma-separated tools calls remove_tool for each name."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "list_tasks,show_task,create_task"}):
            _apply_tool_exclusions(server)

        assert server.remove_tool.call_count == 3
        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert called_names == {"list_tasks", "show_task", "create_task"}

    # AC: Default (no env var set): all 7 tools registered — remove_tool never called
    def test_no_env_var_remove_tool_never_called(self) -> None:
        """When KANBAN_TOOLS_EXCLUDE is not set, remove_tool is never called."""
        server = _make_mock_server()
        env_without_exclude = {k: v for k, v in os.environ.items() if k != "KANBAN_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without_exclude, clear=True):
            _apply_tool_exclusions(server)

        server.remove_tool.assert_not_called()

    # AC: Default (empty env var): backwards-compatible — remove_tool never called
    def test_empty_env_var_remove_tool_never_called(self) -> None:
        """When KANBAN_TOOLS_EXCLUDE is set to empty string, remove_tool is never called."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": ""}):
            _apply_tool_exclusions(server)

        server.remove_tool.assert_not_called()

    # AC: strip whitespace from comma-separated names
    def test_whitespace_stripped_from_tool_names(self) -> None:
        """Leading/trailing whitespace around each tool name is stripped before calling remove_tool."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": " list_tasks ,  show_task "}):
            _apply_tool_exclusions(server)

        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert "list_tasks" in called_names
        assert "show_task" in called_names
        # raw names with whitespace must NOT appear
        assert any(" " in name for name in called_names) is False

    # AC: Invalid/unknown tool names silently ignored (try/except around remove_tool)
    def test_invalid_tool_name_does_not_raise(self) -> None:
        """An unknown tool name causes remove_tool to raise, but the exception is swallowed."""
        server = _make_mock_server()
        server.remove_tool.side_effect = Exception("unknown tool: no_such_tool")
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "no_such_tool"}):
            # Must not raise — exception must be silently ignored
            _apply_tool_exclusions(server)

    # AC: Invalid name ignored, valid names still processed
    def test_invalid_name_mixed_with_valid_still_excludes_valid(self) -> None:
        """When the list contains both valid and invalid names, valid names are still excluded."""
        call_log: list[str] = []

        def _selective_remove(name: str) -> None:
            if name == "no_such_tool":
                msg = "unknown tool"
                raise ValueError(msg)
            call_log.append(name)

        server = _make_mock_server()
        server.remove_tool.side_effect = _selective_remove
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "list_tasks,no_such_tool,show_task"}):
            _apply_tool_exclusions(server)

        assert "list_tasks" in call_log
        assert "show_task" in call_log

    # AC: returns set[str]
    def test_returns_set_type(self) -> None:
        """_apply_tool_exclusions returns a set (set[str])."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "list_tasks"}):
            result = _apply_tool_exclusions(server)

        assert isinstance(result, set)

    # AC: return set contains the names that were successfully excluded
    def test_returns_empty_set_when_no_env_var(self) -> None:
        """_apply_tool_exclusions returns an empty set when no env var is set."""
        server = _make_mock_server()
        env_without_exclude = {k: v for k, v in os.environ.items() if k != "KANBAN_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without_exclude, clear=True):
            result = _apply_tool_exclusions(server)

        assert result == set()

    # Boundary: all 7 known tool names can be passed without error
    def test_all_seven_tool_names_accepted(self) -> None:
        """All 7 canonical tool names can be listed in KANBAN_TOOLS_EXCLUDE without error."""
        server = _make_mock_server()
        all_tools = "list_tasks,show_task,create_task,move_task,edit_task,pick_task,board_context"
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": all_tools}):
            _apply_tool_exclusions(server)

        assert server.remove_tool.call_count == 7

    # Edge: single trailing comma should not produce an empty-string tool call
    def test_trailing_comma_ignored(self) -> None:
        """A trailing comma in KANBAN_TOOLS_EXCLUDE does not call remove_tool with an empty string."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "list_tasks,"}):
            _apply_tool_exclusions(server)

        called_names = [call.args[0] for call in server.remove_tool.call_args_list]
        assert "" not in called_names


# ---------------------------------------------------------------------------
# TestFromAC_LifespanToolExclusion
# ---------------------------------------------------------------------------


class TestFromAC_LifespanToolExclusion:
    """Contract tests for app_lifespan integration with tool exclusion from #491 AC."""

    # AC: _apply_tool_exclusions is called inside app_lifespan before yield
    @pytest.mark.asyncio
    async def test_lifespan_calls_apply_tool_exclusions(self) -> None:
        """app_lifespan calls _apply_tool_exclusions during startup (before yield)."""
        mock_server = MagicMock()
        with (
            patch("owlbear_mcp_kanban.server.Path.exists", return_value=True),
            patch("owlbear_mcp_kanban.server._apply_tool_exclusions") as mock_apply,
        ):
            async with app_lifespan(mock_server):
                # By the time we reach the body, _apply_tool_exclusions must have been called
                mock_apply.assert_called_once()

    # AC: _apply_tool_exclusions receives the server object
    @pytest.mark.asyncio
    async def test_lifespan_passes_server_to_apply_tool_exclusions(self) -> None:
        """app_lifespan passes the server argument to _apply_tool_exclusions."""
        mock_server = MagicMock()
        with (
            patch("owlbear_mcp_kanban.server.Path.exists", return_value=True),
            patch("owlbear_mcp_kanban.server._apply_tool_exclusions") as mock_apply,
        ):
            async with app_lifespan(mock_server):
                call_args = mock_apply.call_args
                assert call_args is not None
                # first positional arg must be the server
                assert call_args.args[0] is mock_server

    # AC: Default (no env var): all 7 tools registered — remove_tool never called during lifespan
    @pytest.mark.asyncio
    async def test_lifespan_default_no_tool_removals(self) -> None:
        """With no KANBAN_TOOLS_EXCLUDE set, no tools are removed during lifespan startup."""
        mock_server = MagicMock()
        mock_server.remove_tool = MagicMock()
        env_without_exclude = {k: v for k, v in os.environ.items() if k != "KANBAN_TOOLS_EXCLUDE"}
        with (
            patch.dict(os.environ, env_without_exclude, clear=True),
            patch("owlbear_mcp_kanban.server.Path.exists", return_value=True),
        ):
            async with app_lifespan(mock_server):
                pass

        mock_server.remove_tool.assert_not_called()

    # AC: lifespan with KANBAN_TOOLS_EXCLUDE set removes the specified tool
    @pytest.mark.asyncio
    async def test_lifespan_removes_tool_when_env_var_set(self) -> None:
        """app_lifespan removes tools specified in KANBAN_TOOLS_EXCLUDE during startup."""
        mock_server = MagicMock()
        mock_server.remove_tool = MagicMock()
        with (
            patch.dict(os.environ, {"KANBAN_TOOLS_EXCLUDE": "list_tasks"}),
            patch("owlbear_mcp_kanban.server.Path.exists", return_value=True),
        ):
            async with app_lifespan(mock_server):
                pass

        mock_server.remove_tool.assert_called_with("list_tasks")
