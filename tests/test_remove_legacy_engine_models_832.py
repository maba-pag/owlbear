"""RED tests — AC4: All 8 MCP tools remain accessible after engine_models removal (#832).

AC coverage:
  AC1 - engine_models.py absent (precondition checked in each test, same as #831 AC1)
  AC4 - All 8 MCP tool functions importable and registered in the mcp server object
  AC4 - pick_tasks is the 8th tool (not in test_tool_annotations_494.py parametrize — gap filled here)
  AC4 - Exactly 8 tools registered (boundary)

All tests FAIL in RED phase: each test asserts engine_models.py is gone as its first assertion.
The file still exists → AssertionError → every test is RED.

After implementation: engine_models.py deleted → precondition passes → all assertions verified.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_ENGINE_MODELS_PATH = (
    _REPO_ROOT / "serve" / "mcp-kanban" / "src" / "owlbear_mcp_kanban" / "engine_models.py"
)

_8_TOOLS = frozenset(
    {
        "create_task",
        "edit_task",
        "end_work",
        "list_tasks",
        "move_task",
        "pick_tasks",
        "show_task",
        "start_work",
    }
)

_AC1_MSG = (
    f"AC1 precondition: engine_models.py still exists at {_ENGINE_MODELS_PATH}. "
    "Delete it (AC1) before verifying AC4 tool accessibility."
)


def _registered_tool_names() -> set[str]:
    """Return the set of tool names registered in the mcp server object."""
    from owlbear_mcp_kanban.server import mcp  # noqa: PLC0415

    names: set[str] = set()
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            name = getattr(t, "name", None)
            if name is not None:
                names.add(name)
    return names


class TestFromAC_ServerToolsAfterEngineModelsRemoval:
    """AC4: All 8 MCP tools remain importable and registered after engine_models.py is deleted."""

    # ------------------------------------------------------------------
    # Happy path — all 8 tools importable from the server module
    # ------------------------------------------------------------------

    def test_all_8_tools_importable_from_server_module(self) -> None:
        """All 8 MCP tool functions must be importable from owlbear_mcp_kanban.server."""
        assert not _ENGINE_MODELS_PATH.exists(), _AC1_MSG

        from owlbear_mcp_kanban.server import (  # noqa: PLC0415
            create_task,
            edit_task,
            end_work,
            list_tasks,
            move_task,
            pick_tasks,
            show_task,
            start_work,
        )

        tools = [create_task, edit_task, end_work, list_tasks, move_task, pick_tasks, show_task, start_work]
        for tool in tools:
            assert callable(tool), f"Expected {tool!r} to be callable after migration"

    def test_all_8_tool_names_in_server_all_exports(self) -> None:
        """All 8 tool names must appear in owlbear_mcp_kanban.server.__all__."""
        assert not _ENGINE_MODELS_PATH.exists(), _AC1_MSG

        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        exported = set(server_mod.__all__)
        missing = _8_TOOLS - exported
        assert not missing, (
            f"These tools are missing from server.__all__ after engine_models removal: {sorted(missing)}"
        )

    # ------------------------------------------------------------------
    # Edge — pick_tasks (8th tool, absent from test_tool_annotations_494 parametrize)
    # ------------------------------------------------------------------

    def test_pick_tasks_registered_in_mcp_server(self) -> None:
        """pick_tasks must be registered with the mcp server object (8th tool coverage gap)."""
        assert not _ENGINE_MODELS_PATH.exists(), _AC1_MSG

        registered = _registered_tool_names()
        assert "pick_tasks" in registered, (
            "pick_tasks is not registered in the mcp server; "
            "it is the 8th MCP tool required by AC4 and was absent from "
            "test_tool_annotations_494.py parametrize list"
        )

    def test_pick_tasks_has_read_only_hint(self) -> None:
        """pick_tasks must have readOnlyHint=True (8th tool, previously untested annotation)."""
        assert not _ENGINE_MODELS_PATH.exists(), _AC1_MSG

        from owlbear_mcp_kanban.server import mcp  # noqa: PLC0415

        annotation = None
        if hasattr(mcp, "_tool_manager"):
            for t in mcp._tool_manager.list_tools():  # noqa: SLF001
                if getattr(t, "name", None) == "pick_tasks":
                    annotation = getattr(t, "annotations", None)
                    break

        assert annotation is not None, "pick_tasks must have ToolAnnotations registered"
        assert annotation.readOnlyHint is True, (  # type: ignore[union-attr]
            f"pick_tasks readOnlyHint must be True, got: {annotation.readOnlyHint!r}"
        )

    # ------------------------------------------------------------------
    # Boundary — exactly 8 tools registered (not 7, not 9)
    # ------------------------------------------------------------------

    def test_mcp_server_registers_exactly_8_tools(self) -> None:
        """The mcp server must register exactly the 8 known tools — no tool lost in migration."""
        assert not _ENGINE_MODELS_PATH.exists(), _AC1_MSG

        registered = _registered_tool_names()
        missing = _8_TOOLS - registered
        extra = registered - _8_TOOLS

        assert not missing, (
            f"These tools were lost after engine_models removal: {sorted(missing)}"
        )
        assert not extra, (
            f"Unexpected extra tools registered: {sorted(extra)}. "
            "Verify the migration did not introduce phantom tool registrations."
        )

    # ------------------------------------------------------------------
    # Error — engine_models must not be importable after deletion
    # ------------------------------------------------------------------

    def test_engine_models_not_importable_as_submodule(self) -> None:
        """owlbear_mcp_kanban.engine_models must not be importable after engine_models.py is deleted."""
        # This test checks the import mechanism (importlib), complementing #831's
        # filesystem check (pathlib). Both must pass for a complete AC1 signal.
        spec = importlib.util.find_spec("owlbear_mcp_kanban.engine_models")
        assert spec is None, (
            "owlbear_mcp_kanban.engine_models is still importable as a Python module. "
            "Delete engine_models.py to complete AC1 and unblock AC4 tool tests."
        )
