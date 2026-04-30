"""Failing tests for removal of KANBAN_TOOLS_EXCLUDE / _apply_tool_exclusions (#1199).

AC coverage:
  - _apply_tool_exclusions function removed from server.py (td:1)
  - _apply_tool_exclusions call removed from app_lifespan (td:1)
  - Server starts and registers all tools normally (td:1) [regression guard]
  - outputSchema and _patch_params functionality preserved (td:1) [regression guard]
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import owlbear_mcp_kanban.server as srv
from owlbear_mcp_kanban.server import app_lifespan, mcp


# ---------------------------------------------------------------------------
# TestFromAC_FunctionRemoval
# AC: _apply_tool_exclusions function removed from server.py (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_FunctionRemoval:
    """_apply_tool_exclusions must not be importable from the server module."""

    def test_apply_tool_exclusions_not_in_server_module(self) -> None:
        """_apply_tool_exclusions is absent from owlbear_mcp_kanban.server.

        FAILS now: the attribute currently exists on the module.
        PASSES after: builder removes the function.
        """
        assert not hasattr(srv, "_apply_tool_exclusions")


# ---------------------------------------------------------------------------
# TestFromAC_LifespanCallRemoval
# AC: _apply_tool_exclusions call removed from app_lifespan (td:1)
# AC: Server starts and registers all tools normally (td:1) — covered here too
# ---------------------------------------------------------------------------


class TestFromAC_LifespanCallRemoval:
    """app_lifespan must not invoke server.remove_tool for KANBAN_TOOLS_EXCLUDE."""

    @pytest.mark.asyncio
    async def test_lifespan_does_not_remove_tools_when_env_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With KANBAN_TOOLS_EXCLUDE set, lifespan never calls server.remove_tool.

        FAILS now: _apply_tool_exclusions IS called inside app_lifespan and it
        calls server.remove_tool("list_tasks") when the env var is set.
        PASSES after: builder removes the _apply_tool_exclusions call from
        app_lifespan so no tool removal can occur.
        """
        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "list_tasks")
        mock_engine = MagicMock()
        with patch("owlbear_mcp_kanban.server.KanbanEngine", return_value=mock_engine):
            server_mock = MagicMock()
            async with app_lifespan(server_mock) as _ctx:
                server_mock.remove_tool.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_OutputSchemaPreserved
# AC: Existing outputSchema and _patch_params functionality preserved (td:1)
# [regression guard — passes now; would fail if builder over-deletes]
# ---------------------------------------------------------------------------


class TestFromAC_OutputSchemaPreserved:
    """outputSchema patch on list_tasks tool must survive the deletion."""

    def test_list_tasks_output_schema_is_patched(self) -> None:
        """list_tasks tool has a non-None custom outputSchema applied at import.

        Regression guard: currently PASSES because the patch IS applied.
        Would FAIL if the builder accidentally removes the outputSchema block
        together with the _apply_tool_exclusions code.
        """
        tool_obj = next(
            t
            for t in mcp._tool_manager._tools.values()  # noqa: SLF001
            if t.name == "list_tasks"
        )
        schema = tool_obj.fn_metadata.output_schema
        assert schema is not None
        # Must contain at least one top-level JSON Schema key
        assert any(k in schema for k in ("type", "properties", "$defs", "items"))
