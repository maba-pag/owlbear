"""Tests for task #502: Add ToolAnnotations to mcp-project server (TDD RED).

AC coverage:
  - AC1: Import ToolAnnotations from mcp.types (server module attribute test)
  - AC2: project_info: readOnlyHint=True, idempotentHint=True
  - AC3: project_list: readOnlyHint=True, idempotentHint=True
  - AC4: project_readme: readOnlyHint=True, idempotentHint=True
  - AC5: project_structure: readOnlyHint=True, idempotentHint=True
  - AC6: outputSchema auto-generated — all 4 tools already have return type annotations
         in server.py; no new tests needed (would pass immediately).

All tests FAIL in RED phase — ToolAnnotations not yet applied to @mcp.tool() decorators.
"""

from __future__ import annotations

import pytest

from owlbear_mcp_project.server import mcp


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named mcp-project tool, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_ProjectToolAnnotations
# ---------------------------------------------------------------------------


class TestFromAC_ProjectToolAnnotations:
    """Contract tests verifying ToolAnnotations on all mcp-project tools."""

    # -- AC1: ToolAnnotations import ------------------------------------------

    def test_tool_annotations_used_in_server_module(self) -> None:
        """server module must import ToolAnnotations from mcp.types."""
        import owlbear_mcp_project.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "ToolAnnotations"), (
            "server module must import ToolAnnotations so it can be used in @mcp.tool() decorators"
        )

    # -- All 4 tools must have annotations (not None) -------------------------

    @pytest.mark.parametrize(
        "tool_name",
        [
            "project_info",
            "project_list",
            "project_readme",
            "project_structure",
        ],
    )
    def test_all_tools_have_annotations(self, tool_name: str) -> None:
        """Every mcp-project tool must have a ToolAnnotations object registered."""
        annotations = _get_tool_annotations(tool_name)
        assert annotations is not None, (
            f"Tool '{tool_name}' has no ToolAnnotations; "
            "add annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True) "
            "to its @mcp.tool() decorator"
        )

    # -- AC2: project_info ----------------------------------------------------

    def test_project_info_read_only_hint_true(self) -> None:
        """project_info is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("project_info")
        assert ann is not None, "project_info has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for project_info, got: {ann.readOnlyHint!r}"
        )

    def test_project_info_idempotent_hint_true(self) -> None:
        """project_info is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("project_info")
        assert ann is not None, "project_info has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for project_info, got: {ann.idempotentHint!r}"
        )

    # -- AC3: project_list ----------------------------------------------------

    def test_project_list_read_only_hint_true(self) -> None:
        """project_list is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("project_list")
        assert ann is not None, "project_list has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for project_list, got: {ann.readOnlyHint!r}"
        )

    def test_project_list_idempotent_hint_true(self) -> None:
        """project_list is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("project_list")
        assert ann is not None, "project_list has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for project_list, got: {ann.idempotentHint!r}"
        )

    # -- AC4: project_readme --------------------------------------------------

    def test_project_readme_read_only_hint_true(self) -> None:
        """project_readme is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("project_readme")
        assert ann is not None, "project_readme has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for project_readme, got: {ann.readOnlyHint!r}"
        )

    def test_project_readme_idempotent_hint_true(self) -> None:
        """project_readme is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("project_readme")
        assert ann is not None, "project_readme has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for project_readme, got: {ann.idempotentHint!r}"
        )

    # -- AC5: project_structure -----------------------------------------------

    def test_project_structure_read_only_hint_true(self) -> None:
        """project_structure is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("project_structure")
        assert ann is not None, "project_structure has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for project_structure, got: {ann.readOnlyHint!r}"
        )

    def test_project_structure_idempotent_hint_true(self) -> None:
        """project_structure is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("project_structure")
        assert ann is not None, "project_structure has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for project_structure, got: {ann.idempotentHint!r}"
        )
