"""Tests for task #494: ToolAnnotations on all mcp-kanban tools (TDD RED).

AC coverage:
  - list_tasks:    readOnlyHint=True,  idempotentHint=True
  - show_task:     readOnlyHint=True,  idempotentHint=True
  - create_task:   destructiveHint=False
    - move_task:     destructiveHint=False, idempotentHint=False
  - edit_task:     destructiveHint=False
  - start_work:    destructiveHint=False
  - end_work:      destructiveHint=False
  - ToolAnnotations imported from mcp.types in server module
  - All 7 tools have annotations (not None)

All tests FAIL in RED phase — ToolAnnotations not yet applied to @mcp.tool() decorators.
"""

from __future__ import annotations

import pytest

from owlbear_mcp_kanban.server import mcp


# ---------------------------------------------------------------------------
# Helper — mirrors _get_tool_annotations from mcp-knowledge tests
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named tool, or None if not found."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_ToolAnnotations
# ---------------------------------------------------------------------------


class TestFromAC_ToolAnnotations:
    """Contract tests verifying ToolAnnotations are registered on every mcp-kanban tool."""

    # -- ToolAnnotations import -----------------------------------------------

    def test_tool_annotations_used_in_server_module(self) -> None:
        """server module must import ToolAnnotations from mcp.types."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "ToolAnnotations"), (
            "server module must import ToolAnnotations so it can be used in @mcp.tool() decorators"
        )

    # -- All 7 tools have annotations (not None) ------------------------------

    @pytest.mark.parametrize(
        "tool_name",
        [
            "list_tasks",
            "show_task",
            "create_task",
            "move_task",
            "edit_task",
            "start_work",
            "end_work",
        ],
    )
    def test_all_tools_have_annotations(self, tool_name: str) -> None:
        """Every mcp-kanban tool must have a ToolAnnotations object registered."""
        annotations = _get_tool_annotations(tool_name)
        assert annotations is not None, (
            f"Tool '{tool_name}' has no ToolAnnotations; "
            "add annotations=ToolAnnotations(...) to its @mcp.tool() decorator"
        )

    # -- list_tasks -----------------------------------------------------------

    def test_list_tasks_read_only_hint_true(self) -> None:
        """list_tasks is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("list_tasks")
        assert ann is not None, "list_tasks has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for list_tasks, got: {ann.readOnlyHint!r}"
        )

    def test_list_tasks_idempotent_hint_true(self) -> None:
        """list_tasks is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("list_tasks")
        assert ann is not None, "list_tasks has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for list_tasks, got: {ann.idempotentHint!r}"
        )

    # -- show_task ------------------------------------------------------------

    def test_show_task_read_only_hint_true(self) -> None:
        """show_task is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("show_task")
        assert ann is not None, "show_task has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for show_task, got: {ann.readOnlyHint!r}"
        )

    def test_show_task_idempotent_hint_true(self) -> None:
        """show_task is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("show_task")
        assert ann is not None, "show_task has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for show_task, got: {ann.idempotentHint!r}"
        )

    # -- create_task ----------------------------------------------------------

    def test_create_task_destructive_hint_false(self) -> None:
        """create_task is additive: destructiveHint must be False."""
        ann = _get_tool_annotations("create_task")
        assert ann is not None, "create_task has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for create_task, got: {ann.destructiveHint!r}"
        )

    # -- move_task ------------------------------------------------------------

    def test_move_task_destructive_hint_false(self) -> None:
        """move_task is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("move_task")
        assert ann is not None, "move_task has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for move_task, got: {ann.destructiveHint!r}"
        )

    def test_move_task_idempotent_hint_false(self) -> None:
        """move_task is non-idempotent: idempotentHint must be False."""
        ann = _get_tool_annotations("move_task")
        assert ann is not None, "move_task has no ToolAnnotations"
        assert ann.idempotentHint is False, (  # type: ignore[union-attr]
            f"Expected idempotentHint=False for move_task, got: {ann.idempotentHint!r}"
        )

    # -- edit_task ------------------------------------------------------------

    def test_edit_task_destructive_hint_false(self) -> None:
        """edit_task is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("edit_task")
        assert ann is not None, "edit_task has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for edit_task, got: {ann.destructiveHint!r}"
        )

    # -- start_work -----------------------------------------------------------

    def test_start_work_destructive_hint_false(self) -> None:
        """start_work is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("start_work")
        assert ann is not None, "start_work has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for start_work, got: {ann.destructiveHint!r}"
        )

    # -- end_work -------------------------------------------------------------

    def test_end_work_destructive_hint_false(self) -> None:
        """end_work is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("end_work")
        assert ann is not None, "end_work has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for end_work, got: {ann.destructiveHint!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_AnnotationContractRestore_1475  (retry-1475 required follow-up)
# ---------------------------------------------------------------------------


class TestFromAC_AnnotationContractRestore_1475:
    """Retry-1475 updated contract: move_task idempotentHint must be False.

    The move_task tool mutates status and emits activity on each invocation, so
    idempotentHint=False is the correct contract for MCP consumers.
    """

    def test_move_task_idempotent_hint_false_per_updated_contract(self) -> None:
        """move_task idempotentHint must be False per the updated AC contract."""
        ann = _get_tool_annotations("move_task")
        assert ann is not None, "move_task has no ToolAnnotations"
        assert ann.idempotentHint is False, (  # type: ignore[union-attr]
            f"Updated AC requires idempotentHint=False for move_task; got: {ann.idempotentHint!r}."
        )
