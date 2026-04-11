"""Tests for task #770: ToolAnnotations on all mcp-browser tools.

AC coverage:
  - navigate:   idempotentHint=True, destructiveHint=False
  - click:      destructiveHint=False
  - type:       destructiveHint=False
  - select:     idempotentHint=True, destructiveHint=False
  - read_text:  readOnlyHint=True, idempotentHint=True
  - snapshot:   readOnlyHint=True, idempotentHint=True
  - ToolAnnotations imported from mcp.types in server module
  - All 6 tools have annotations (not None)
"""

from __future__ import annotations

import pytest

from owlbear_mcp_browser.server import mcp_app


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named tool, or None if not found."""
    for t in mcp_app.list_tools():
        if getattr(t, "name", None) == tool_name:
            return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_ToolAnnotations
# ---------------------------------------------------------------------------


class TestFromAC_ToolAnnotations:
    """Contract tests verifying ToolAnnotations are registered on every mcp-browser tool."""

    # -- ToolAnnotations import -----------------------------------------------

    def test_tool_annotations_used_in_server_module(self) -> None:
        """server module must import ToolAnnotations from mcp.types."""
        import owlbear_mcp_browser.server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "ToolAnnotations"), (
            "server module must import ToolAnnotations so it can be used in @_mcp.tool() decorators"
        )

    # -- All 6 tools have annotations (not None) ------------------------------

    @pytest.mark.parametrize(
        "tool_name",
        [
            "navigate",
            "click",
            "type",
            "select",
            "read_text",
            "snapshot",
        ],
    )
    def test_all_tools_have_annotations(self, tool_name: str) -> None:
        """Every mcp-browser tool must have a ToolAnnotations object registered."""
        annotations = _get_tool_annotations(tool_name)
        assert annotations is not None, (
            f"Tool '{tool_name}' has no ToolAnnotations; "
            "add annotations=ToolAnnotations(...) to its @_mcp.tool() decorator"
        )

    # -- read_text ------------------------------------------------------------

    def test_read_text_read_only_hint_true(self) -> None:
        """read_text is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("read_text")
        assert ann is not None, "read_text has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for read_text, got: {ann.readOnlyHint!r}"
        )

    def test_read_text_idempotent_hint_true(self) -> None:
        """read_text is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("read_text")
        assert ann is not None, "read_text has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for read_text, got: {ann.idempotentHint!r}"
        )

    # -- snapshot -------------------------------------------------------------

    def test_snapshot_read_only_hint_true(self) -> None:
        """snapshot is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("snapshot")
        assert ann is not None, "snapshot has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for snapshot, got: {ann.readOnlyHint!r}"
        )

    def test_snapshot_idempotent_hint_true(self) -> None:
        """snapshot is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("snapshot")
        assert ann is not None, "snapshot has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for snapshot, got: {ann.idempotentHint!r}"
        )

    # -- navigate -------------------------------------------------------------

    def test_navigate_idempotent_hint_true(self) -> None:
        """navigate is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("navigate")
        assert ann is not None, "navigate has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for navigate, got: {ann.idempotentHint!r}"
        )

    def test_navigate_destructive_hint_false(self) -> None:
        """navigate is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("navigate")
        assert ann is not None, "navigate has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for navigate, got: {ann.destructiveHint!r}"
        )

    # -- select ---------------------------------------------------------------

    def test_select_idempotent_hint_true(self) -> None:
        """select is idempotent: idempotentHint must be True."""
        ann = _get_tool_annotations("select")
        assert ann is not None, "select has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for select, got: {ann.idempotentHint!r}"
        )

    def test_select_destructive_hint_false(self) -> None:
        """select is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("select")
        assert ann is not None, "select has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for select, got: {ann.destructiveHint!r}"
        )

    # -- click ----------------------------------------------------------------

    def test_click_destructive_hint_false(self) -> None:
        """click is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("click")
        assert ann is not None, "click has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for click, got: {ann.destructiveHint!r}"
        )

    # -- type -----------------------------------------------------------------

    def test_type_destructive_hint_false(self) -> None:
        """type is non-destructive: destructiveHint must be False."""
        ann = _get_tool_annotations("type")
        assert ann is not None, "type has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for type, got: {ann.destructiveHint!r}"
        )
