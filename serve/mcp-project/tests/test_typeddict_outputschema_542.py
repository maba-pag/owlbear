"""Tests for task #543: TypedDict return types for outputSchema on mcp-project (TDD RED).

AC coverage:
  - AC1: Schema-pinning — project_info output_schema has top-level properties
         with keys: name, type, project_path, owlbear_path, created_at (all type: string)
  - AC2: Schema-pinning — project_list output_schema has items schema containing
         name and path properties (inside FastMCP result wrapper)
  - AC3: ToolError — project_info raises ToolError (mcp.server.fastmcp.exceptions)
         when project_file is None

All tests FAIL in RED phase — TypedDicts and ToolError not yet implemented.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_project.server import AppContext, mcp, project_info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tool_obj(tool_name: str) -> Any:
    """Return the FastMCP tool object for the named tool, or None."""
    if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):  # noqa: SLF001
        return mcp._tool_manager._tools.get(tool_name)  # noqa: SLF001
    return None


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    """Return a MagicMock mimicking an MCP Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or AppContext(
        project_file=None,
        project_root=MagicMock(),
        owlbear_root=MagicMock(),
    )
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_ProjectInfoOutputSchema  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_ProjectInfoOutputSchema:
    """Schema-pinning tests: project_info must return a typed schema via TypedDict."""

    def test_project_info_output_schema_has_properties_key(self) -> None:
        """project_info output_schema has top-level 'properties' with field keys (TypedDict shape).

        Before TypedDict: schema wraps everything in {properties: {result: ...}}.
        After TypedDict: schema has {properties: {name: ..., type: ..., ...}} directly.
        """
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found in mcp._tool_manager._tools"
        schema = tool.fn_metadata.output_schema
        assert "properties" in schema, f"project_info output_schema missing top-level 'properties'; got: {schema}"
        props = schema["properties"]
        # Must not be the generic FastMCP wrapper (only a single 'result' key)
        assert set(props.keys()) != {"result"}, (
            "project_info output_schema is still the generic wrapper schema — "
            "TypedDict return type not yet implemented; props: {list(props)}"
        )

    def test_project_info_output_schema_has_name_property(self) -> None:
        """project_info output_schema has 'name' property of type string."""
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found"
        schema = tool.fn_metadata.output_schema
        props = schema.get("properties", {})
        assert "name" in props, f"'name' missing from project_info properties; got: {list(props)}"
        assert props["name"].get("type") == "string", f"'name' must be type string; got: {props['name']}"

    def test_project_info_output_schema_has_type_property(self) -> None:
        """project_info output_schema has 'type' property of type string."""
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found"
        schema = tool.fn_metadata.output_schema
        props = schema.get("properties", {})
        assert "type" in props, f"'type' missing from project_info properties; got: {list(props)}"
        assert props["type"].get("type") == "string", f"'type' must be type string; got: {props['type']}"

    def test_project_info_output_schema_has_project_path_property(self) -> None:
        """project_info output_schema has 'project_path' property of type string."""
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found"
        schema = tool.fn_metadata.output_schema
        props = schema.get("properties", {})
        assert "project_path" in props, f"'project_path' missing from project_info properties; got: {list(props)}"
        assert props["project_path"].get("type") == "string", (
            f"'project_path' must be type string; got: {props['project_path']}"
        )

    def test_project_info_output_schema_has_owlbear_path_property(self) -> None:
        """project_info output_schema has 'owlbear_path' property of type string."""
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found"
        schema = tool.fn_metadata.output_schema
        props = schema.get("properties", {})
        assert "owlbear_path" in props, f"'owlbear_path' missing from project_info properties; got: {list(props)}"
        assert props["owlbear_path"].get("type") == "string", (
            f"'owlbear_path' must be type string; got: {props['owlbear_path']}"
        )

    def test_project_info_output_schema_has_created_at_property(self) -> None:
        """project_info output_schema has 'created_at' property of type string."""
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found"
        schema = tool.fn_metadata.output_schema
        props = schema.get("properties", {})
        assert "created_at" in props, f"'created_at' missing from project_info properties; got: {list(props)}"
        assert props["created_at"].get("type") == "string", (
            f"'created_at' must be type string; got: {props['created_at']}"
        )

    def test_project_info_output_schema_all_required_fields_present(self) -> None:
        """project_info output_schema has all 5 required fields in properties."""
        tool = _get_tool_obj("project_info")
        assert tool is not None, "project_info tool not found"
        schema = tool.fn_metadata.output_schema
        props = schema.get("properties", {})
        required_keys = {"name", "type", "project_path", "owlbear_path", "created_at"}
        missing = required_keys - set(props)
        assert not missing, f"project_info output_schema missing fields: {missing}; got: {list(props)}"


# ---------------------------------------------------------------------------
# TestFromAC_ProjectListOutputSchema  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_ProjectListOutputSchema:
    """Schema-pinning tests: project_list must have items schema with name+path."""

    def _get_items_schema(self) -> dict[str, Any]:
        """Drill into the output_schema to find the items object schema."""
        tool = _get_tool_obj("project_list")
        assert tool is not None, "project_list tool not found in mcp._tool_manager._tools"
        schema = tool.fn_metadata.output_schema
        # FastMCP wraps list return in: {"properties": {"result": {"items": {...}}}}
        # Navigate to the items level — handle both wrapped and unwrapped forms.
        if "items" in schema:
            return schema["items"]  # type: ignore[return-value]
        if "properties" in schema and "result" in schema["properties"]:
            result_schema = schema["properties"]["result"]
            if "items" in result_schema:
                return result_schema["items"]  # type: ignore[return-value]
        pytest.fail(f"Cannot locate 'items' in project_list output_schema; schema: {schema}")

    def test_project_list_output_schema_has_items(self) -> None:
        """project_list output_schema has 'items' with typed properties (not empty dict).

        Before TypedDict: items.properties is {} (untyped dict[str, str]).
        After TypedDict: items.properties has {name: ..., path: ...}.
        """
        tool = _get_tool_obj("project_list")
        assert tool is not None, "project_list tool not found"
        schema = tool.fn_metadata.output_schema
        # Navigate to items schema
        items: dict[str, object] | None = None
        if "items" in schema:
            items = schema["items"]
        elif (
            "properties" in schema
            and "result" in schema.get("properties", {})
            and "items" in schema["properties"]["result"]
        ):
            items = schema["properties"]["result"]["items"]

        assert items is not None, f"project_list output_schema has no 'items'; schema: {schema}"
        # Must have non-empty properties — generic dict produces {}
        props = items.get("properties", {}) if isinstance(items, dict) else {}
        assert props, (
            f"project_list items.properties is empty — TypedDict return type not yet implemented; items: {items}"
        )

    def test_project_list_items_schema_has_name_property(self) -> None:
        """project_list items schema has 'name' property (TypedDict field)."""
        items = self._get_items_schema()
        props = items.get("properties", {})
        assert "name" in props, f"'name' missing from project_list items properties; got: {list(props)}"

    def test_project_list_items_schema_has_path_property(self) -> None:
        """project_list items schema has 'path' property (TypedDict field)."""
        items = self._get_items_schema()
        props = items.get("properties", {})
        assert "path" in props, f"'path' missing from project_list items properties; got: {list(props)}"

    def test_project_list_items_schema_name_is_string_type(self) -> None:
        """project_list items 'name' property is type string."""
        items = self._get_items_schema()
        props = items.get("properties", {})
        assert "name" in props, "'name' missing from project_list items properties"
        assert props["name"].get("type") == "string", f"'name' must be type string; got: {props['name']}"

    def test_project_list_items_schema_path_is_string_type(self) -> None:
        """project_list items 'path' property is type string."""
        items = self._get_items_schema()
        props = items.get("properties", {})
        assert "path" in props, "'path' missing from project_list items properties"
        assert props["path"].get("type") == "string", f"'path' must be type string; got: {props['path']}"


# ---------------------------------------------------------------------------
# TestFromAC_ProjectInfoToolError  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_ProjectInfoToolError:
    """project_info must raise ToolError when project_file is None."""

    @pytest.mark.asyncio
    async def test_project_info_raises_tool_error_when_no_project_file(self) -> None:
        """project_info raises ToolError (not returns string) when project_file is None."""
        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415

        app_ctx = AppContext(
            project_file=None,
            project_root=MagicMock(),
            owlbear_root=MagicMock(),
        )
        mcp_ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await project_info(mcp_ctx)

    @pytest.mark.asyncio
    async def test_project_info_does_not_return_string_when_no_project_file(self) -> None:
        """project_info must not silently return an error string — must raise."""
        app_ctx = AppContext(
            project_file=None,
            project_root=MagicMock(),
            owlbear_root=MagicMock(),
        )
        mcp_ctx = _make_mcp_ctx(app_ctx)

        # Current implementation returns a string — this must fail once ToolError is raised
        result_is_error_string = False
        try:
            result = await project_info(mcp_ctx)
            result_is_error_string = isinstance(result, str) and result.startswith("error:")
        except Exception:  # noqa: BLE001, S110
            pass

        assert not result_is_error_string, (
            "project_info must raise ToolError, not return an error string, when project_file is None"
        )

    @pytest.mark.asyncio
    async def test_project_info_tool_error_message_describes_missing_config(self) -> None:
        """ToolError message mentions missing config file or project context."""
        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415

        app_ctx = AppContext(
            project_file=None,
            project_root=MagicMock(),
            owlbear_root=MagicMock(),
        )
        mcp_ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError) as exc_info:
            await project_info(mcp_ctx)

        message = str(exc_info.value).lower()
        assert any(keyword in message for keyword in ("project", "config", "owlbear", "json")), (
            f"ToolError message should describe missing config; got: {exc_info.value}"
        )
