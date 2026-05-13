"""RED-phase tests for #1361: Pin FastMCP version + schema assertion tests.

AC coverage:
- AC1: serve/mcp-kanban/pyproject.toml pins the MCP/FastMCP dependency with an upper bound
- AC2: all 5 mutation tools have outputSchema == SingleTaskResponse.model_json_schema()
- AC3: list_tasks has outputSchema == ListTasksResponse.model_json_schema()
- AC4: patched parameter descriptions/enums are present for list_tasks, create_task,
        move_task, edit_task, end_work
- AC5 (meta): tests access the private FastMCP API so they catch breakage at upgrade time

These tests serve as regression guards for the monkey-patching in server.py that
accesses mcp._tool_manager._tools (private API).  If FastMCP changes its internals,
the attribute lookups in the tests will raise AttributeError and make the failure
visible before a silent production breakage.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from owlbear_kanban.models import ListTasksResponse, SingleTaskResponse
from owlbear_mcp_kanban.server import mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PYPROJECT = Path(__file__).parents[1] / "serve" / "mcp-kanban" / "pyproject.toml"

_MUTATION_TOOLS = ["move_task", "edit_task", "create_task", "start_work", "end_work"]


def _get_tool(tool_name: str) -> object:
    """Return the FastMCP tool object for *tool_name*, or raise AssertionError."""
    tool = next(
        (t for t in mcp._tool_manager._tools.values() if t.name == tool_name),  # noqa: SLF001
        None,
    )
    assert tool is not None, (
        f"Tool '{tool_name}' must be registered in mcp._tool_manager._tools. "
        "If FastMCP changed its internal structure, this attribute path is now broken."
    )
    return tool


def _get_tool_props(tool_name: str) -> dict[str, object]:
    """Return the input parameter properties dict for *tool_name*."""
    tool = _get_tool(tool_name)
    props = getattr(tool, "parameters", {}).get("properties", {})
    assert isinstance(props, dict), (
        f"tool.parameters['properties'] for '{tool_name}' must be a dict, "
        f"got {type(props)!r}. FastMCP may have changed its schema structure."
    )
    return props  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# TestFromAC_DependencyVersionPin
# AC1: pyproject.toml pins MCP/FastMCP dependency with upper bound
# ---------------------------------------------------------------------------


class TestFromAC_DependencyVersionPin:
    """AC1: serve/mcp-kanban/pyproject.toml must pin MCP with an upper bound."""

    def test_pyproject_exists(self) -> None:
        """AC1 (precondition): serve/mcp-kanban/pyproject.toml must exist."""
        assert _PYPROJECT.exists(), (
            f"serve/mcp-kanban/pyproject.toml not found at {_PYPROJECT}"
        )

    def test_mcp_dependency_has_upper_bound(self) -> None:
        """AC1: MCP/FastMCP dependency spec must contain '<' (upper bound).

        Accepts any of:
          - mcp[cli]>=1.27.0,<2.0
          - fastmcp>=2.0,<3.0
          - mcp<2.0
        Fails if only a lower bound exists (e.g., mcp[cli]>=1.27.0 with no '<').

        CURRENTLY FAILS: pyproject.toml has 'mcp[cli]>=1.27.0' with no upper bound.
        """
        with _PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)

        deps: list[str] = data.get("project", {}).get("dependencies", [])
        assert deps, (
            "serve/mcp-kanban/pyproject.toml must declare [project.dependencies]"
        )

        mcp_deps = [dep for dep in deps if dep.lower().startswith(("mcp", "fastmcp"))]
        assert mcp_deps, (
            "serve/mcp-kanban/pyproject.toml must list a dependency on 'mcp' or 'fastmcp'. "
            f"Current dependencies: {deps}"
        )

        for spec in mcp_deps:
            assert "<" in spec, (
                f"MCP dependency '{spec}' must include an upper bound (e.g. '<2.0'). "
                "Without an upper bound, a breaking FastMCP upgrade can silently corrupt "
                "the monkey-patched schemas without failing at install time. "
                "Add an upper bound, e.g. 'mcp[cli]>=1.27.0,<2.0'."
            )


# ---------------------------------------------------------------------------
# TestFromAC_MutationToolOutputSchema
# AC2: all 5 mutation tools have outputSchema set to SingleTaskResponse schema
# ---------------------------------------------------------------------------


class TestFromAC_MutationToolOutputSchema:
    """AC2: mutation tools must have fn_metadata.output_schema == SingleTaskResponse schema."""

    @pytest.mark.parametrize("tool_name", _MUTATION_TOOLS)
    def test_mutation_tool_has_output_schema_attribute(self, tool_name: str) -> None:
        """AC2: fn_metadata.output_schema must exist on each mutation tool.

        Fails if FastMCP removes or renames fn_metadata or output_schema.
        """
        tool = _get_tool(tool_name)
        assert hasattr(tool, "fn_metadata"), (
            f"Tool '{tool_name}': FastMCP tool object must have 'fn_metadata' attribute. "
            "FastMCP may have changed its internal structure."
        )
        fn_meta = tool.fn_metadata  # type: ignore[attr-defined]
        assert hasattr(fn_meta, "output_schema"), (
            f"Tool '{tool_name}': fn_metadata must have 'output_schema' attribute. "
            "The schema monkey-patch sets this field; FastMCP may have renamed it."
        )

    @pytest.mark.parametrize("tool_name", _MUTATION_TOOLS)
    def test_mutation_tool_output_schema_equals_single_task_response(
        self, tool_name: str
    ) -> None:
        """AC2: fn_metadata.output_schema must equal SingleTaskResponse.model_json_schema().

        Fails if:
        - The schema monkey-patch in server.py is removed or uses the wrong model
        - FastMCP changes fn_metadata.output_schema semantics
        - The model definition drifts from the registered schema
        """
        tool = _get_tool(tool_name)
        registered = tool.fn_metadata.output_schema  # type: ignore[attr-defined]
        expected = SingleTaskResponse.model_json_schema()
        assert registered == expected, (
            f"Tool '{tool_name}': fn_metadata.output_schema must equal "
            f"SingleTaskResponse.model_json_schema(). "
            f"If FastMCP changes output_schema handling, update the schema monkey-patch "
            f"in server.py. Got: {registered!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksOutputSchema
# AC3: list_tasks has outputSchema set to ListTasksResponse schema
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksOutputSchema:
    """AC3: list_tasks must have fn_metadata.output_schema == ListTasksResponse schema."""

    def test_list_tasks_has_output_schema_attribute(self) -> None:
        """AC3: fn_metadata.output_schema must exist on list_tasks.

        Fails if FastMCP removes or renames fn_metadata or output_schema.
        """
        tool = _get_tool("list_tasks")
        assert hasattr(tool, "fn_metadata"), (
            "Tool 'list_tasks': FastMCP tool object must have 'fn_metadata' attribute."
        )
        fn_meta = tool.fn_metadata  # type: ignore[attr-defined]
        assert hasattr(fn_meta, "output_schema"), (
            "Tool 'list_tasks': fn_metadata must have 'output_schema' attribute. "
            "The schema monkey-patch sets this field; FastMCP may have renamed it."
        )

    def test_list_tasks_output_schema_equals_list_tasks_response(self) -> None:
        """AC3: fn_metadata.output_schema must equal ListTasksResponse.model_json_schema().

        Fails if the schema registration is removed, uses a different model, or
        if FastMCP changes how output_schema is handled.
        """
        tool = _get_tool("list_tasks")
        registered = tool.fn_metadata.output_schema  # type: ignore[attr-defined]
        expected = ListTasksResponse.model_json_schema()
        assert registered == expected, (
            "Tool 'list_tasks': fn_metadata.output_schema must equal "
            f"ListTasksResponse.model_json_schema(). Got: {registered!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_PatchedParameterDescriptions
# AC4: patched parameter descriptions/enums present for all 5 tools
# ---------------------------------------------------------------------------


class TestFromAC_PatchedParameterDescriptions:
    """AC4: _patch_params() must have applied descriptions/enums to tool parameters.

    These tests fail if:
    - FastMCP changes the schema structure so tool.parameters['properties'] no longer exists
    - The _patch_params() call in server.py is removed or targets the wrong key
    - FastMCP rebuilds parameters after module-level patching (wiping patches)
    """

    # -- list_tasks -----------------------------------------------------------

    def test_list_tasks_tag_has_description(self) -> None:
        """AC4: list_tasks.parameters.properties.tag must have a 'description' key."""
        props = _get_tool_props("list_tasks")
        assert "tag" in props, "list_tasks must have a 'tag' parameter property"
        assert "description" in props["tag"], (  # type: ignore[operator]
            "list_tasks 'tag' parameter must have a description patch. "
            "Expected: \"Filter by tag, e.g. 'phase-2'\""
        )

    def test_list_tasks_search_has_description(self) -> None:
        """AC4: list_tasks.parameters.properties.search must have a 'description' key."""
        props = _get_tool_props("list_tasks")
        assert "search" in props, "list_tasks must have a 'search' parameter property"
        assert "description" in props["search"], (  # type: ignore[operator]
            "list_tasks 'search' parameter must have a description patch."
        )

    def test_list_tasks_sort_has_enum(self) -> None:
        """AC4: list_tasks.parameters.properties.sort must have an 'enum' key with valid values."""
        props = _get_tool_props("list_tasks")
        assert "sort" in props, "list_tasks must have a 'sort' parameter property"
        sort_prop = props["sort"]  # type: ignore[index]
        assert "enum" in sort_prop, (  # type: ignore[operator]
            "list_tasks 'sort' parameter must have an 'enum' patch. "
            "Expected enum values: priority, updated, id, title, status, created"
        )
        enum_values: list[str] = sort_prop["enum"]  # type: ignore[index]
        assert set(enum_values) >= {
            "priority",
            "updated",
            "id",
            "title",
            "status",
            "created",
        }, (
            f"list_tasks 'sort' enum must include all sort field names. Got: {enum_values}"
        )

    def test_list_tasks_blocked_has_description(self) -> None:
        """AC4: list_tasks.parameters.properties.blocked must have a 'description' key."""
        props = _get_tool_props("list_tasks")
        assert "blocked" in props, "list_tasks must have a 'blocked' parameter property"
        assert "description" in props["blocked"], (  # type: ignore[operator]
            "list_tasks 'blocked' parameter must have a description patch."
        )

    # -- create_task ----------------------------------------------------------

    def test_create_task_body_has_description(self) -> None:
        """AC4: create_task.parameters.properties.body must have a 'description' key."""
        props = _get_tool_props("create_task")
        assert "body" in props, "create_task must have a 'body' parameter property"
        assert "description" in props["body"], (  # type: ignore[operator]
            "create_task 'body' parameter must have a description patch."
        )

    def test_create_task_depends_on_has_description(self) -> None:
        """AC4: create_task.parameters.properties.depends_on must have a 'description' key."""
        props = _get_tool_props("create_task")
        assert "depends_on" in props, (
            "create_task must have a 'depends_on' parameter property"
        )
        assert "description" in props["depends_on"], (  # type: ignore[operator]
            "create_task 'depends_on' parameter must have a description patch."
        )

    # -- move_task ------------------------------------------------------------

    def test_move_task_status_has_description(self) -> None:
        """AC4: move_task.parameters.properties.status must have a 'description' key."""
        props = _get_tool_props("move_task")
        assert "status" in props, "move_task must have a 'status' parameter property"
        assert "description" in props["status"], (  # type: ignore[operator]
            "move_task 'status' parameter must have a description patch."
        )

    # -- edit_task ------------------------------------------------------------

    def test_edit_task_title_has_description(self) -> None:
        """AC4: edit_task.parameters.properties.title must have a 'description' key."""
        props = _get_tool_props("edit_task")
        assert "title" in props, "edit_task must have a 'title' parameter property"
        assert "description" in props["title"], (  # type: ignore[operator]
            "edit_task 'title' parameter must have a description patch."
        )

    def test_edit_task_append_body_has_description(self) -> None:
        """AC4: edit_task.parameters.properties.append_body must have a 'description' key."""
        props = _get_tool_props("edit_task")
        assert "append_body" in props, (
            "edit_task must have an 'append_body' parameter property"
        )
        assert "description" in props["append_body"], (  # type: ignore[operator]
            "edit_task 'append_body' parameter must have a description patch."
        )

    def test_edit_task_add_dep_has_description(self) -> None:
        """AC4: edit_task.parameters.properties.add_dep must have a 'description' key."""
        props = _get_tool_props("edit_task")
        assert "add_dep" in props, "edit_task must have an 'add_dep' parameter property"
        assert "description" in props["add_dep"], (  # type: ignore[operator]
            "edit_task 'add_dep' parameter must have a description patch."
        )

    # -- end_work -------------------------------------------------------------

    def test_end_work_note_has_description(self) -> None:
        """AC4: end_work.parameters.properties.note must have a 'description' key."""
        props = _get_tool_props("end_work")
        assert "note" in props, "end_work must have a 'note' parameter property"
        assert "description" in props["note"], (  # type: ignore[operator]
            "end_work 'note' parameter must have a description patch."
        )

    def test_end_work_outcome_has_description(self) -> None:
        """AC4: end_work.parameters.properties.outcome must have a 'description' key."""
        props = _get_tool_props("end_work")
        assert "outcome" in props, "end_work must have an 'outcome' parameter property"
        assert "description" in props["outcome"], (  # type: ignore[operator]
            "end_work 'outcome' parameter must have a description patch."
        )

    def test_end_work_block_reason_has_description(self) -> None:
        """AC4: end_work.parameters.properties.block_reason must have a 'description' key."""
        props = _get_tool_props("end_work")
        assert "block_reason" in props, (
            "end_work must have a 'block_reason' parameter property"
        )
        assert "description" in props["block_reason"], (  # type: ignore[operator]
            "end_work 'block_reason' parameter must have a description patch."
        )

    def test_end_work_move_to_has_description(self) -> None:
        """AC4: end_work.parameters.properties.move_to must have a 'description' key."""
        props = _get_tool_props("end_work")
        assert "move_to" in props, "end_work must have a 'move_to' parameter property"
        assert "description" in props["move_to"], (  # type: ignore[operator]
            "end_work 'move_to' parameter must have a description patch."
        )
