"""RED-phase tests for #794: owlbear_mcp_browser MCP server and domain allowlist.

AC coverage:
  AC-annotations: Each of the 6 MCP tools must carry ALL THREE ToolAnnotations hints
    (readOnlyHint, idempotentHint, destructiveHint) explicitly set — not None.

    AC says: "6 MCP tools registered: navigate, click, type, select, read_text, snapshot
              — each with ToolAnnotations (readOnlyHint, idempotentHint, destructiveHint)"

    The existing tests (#770, #771) check individual hints per tool but leave 6
    combinations untested:
      navigate   → readOnlyHint (False: navigate is NOT read-only)
      click      → idempotentHint (False: clicking same element twice is NOT idempotent)
      type       → idempotentHint (False: typing same text twice appends — NOT idempotent)
      select     → readOnlyHint (False: selecting an option mutates form state)
      read_text  → destructiveHint (False: reading text has no destructive side-effects)
      snapshot   → destructiveHint (False: capturing snapshot has no destructive side-effects)

All tests MUST FAIL at RED phase:
  - navigate.readOnlyHint is None (not False)  → assert Ann.readOnlyHint is False → FAIL
  - click.idempotentHint is None (not False)   → assert ann.idempotentHint is False → FAIL
  - type.idempotentHint is None (not False)    → assert ann.idempotentHint is False → FAIL
  - select.readOnlyHint is None (not False)    → assert ann.readOnlyHint is False → FAIL
  - read_text.destructiveHint is None (not False) → assert ann.destructiveHint is False → FAIL
  - snapshot.destructiveHint is None (not False)  → assert ann.destructiveHint is False → FAIL
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named mcp-browser tool, or None."""
    from owlbear_mcp_browser.server import mcp_app

    for t in mcp_app.list_tools():
        if getattr(t, "name", None) == tool_name:
            return getattr(t, "annotations", None)
    return None


# ===========================================================================
# TestFromAC_ToolAnnotationsComplete
# AC: each tool has readOnlyHint, idempotentHint, destructiveHint — all set
# ===========================================================================


class TestFromAC_ToolAnnotationsComplete:
    """All 6 mcp-browser tools must have all 3 explicit ToolAnnotation hints (#794 AC)."""

    # -- navigate: readOnlyHint -----------------------------------------------

    def test_navigate_read_only_hint_is_false(self) -> None:
        """navigate is NOT read-only — it changes the active page in the browser.

        readOnlyHint must be explicitly False, not None.
        """
        ann = _get_tool_annotations("navigate")
        assert ann is not None, "navigate has no ToolAnnotations"
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False for navigate (page state changes on navigation), got: {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    # -- click: idempotentHint ------------------------------------------------

    def test_click_idempotent_hint_is_false(self) -> None:
        """click is NOT idempotent — clicking the same element twice has distinct effects
        (e.g. double-click, toggle, submit-twice).

        idempotentHint must be explicitly False, not None.
        """
        ann = _get_tool_annotations("click")
        assert ann is not None, "click has no ToolAnnotations"
        assert ann.idempotentHint is False, (  # type: ignore[union-attr]
            f"Expected idempotentHint=False for click (repeated clicks have cumulative effects), "
            f"got: {ann.idempotentHint!r}"  # type: ignore[union-attr]
        )

    # -- type: idempotentHint -------------------------------------------------

    def test_type_idempotent_hint_is_false(self) -> None:
        """type is NOT idempotent — typing the same text twice appends to the field.

        idempotentHint must be explicitly False, not None.
        """
        ann = _get_tool_annotations("type")
        assert ann is not None, "'type' tool has no ToolAnnotations"
        assert ann.idempotentHint is False, (  # type: ignore[union-attr]
            f"Expected idempotentHint=False for 'type' (repeated calls append text), got: {ann.idempotentHint!r}"  # type: ignore[union-attr]
        )

    # -- select: readOnlyHint -------------------------------------------------

    def test_select_read_only_hint_is_false(self) -> None:
        """select is NOT read-only — selecting a dropdown option mutates the form element's state.

        readOnlyHint must be explicitly False, not None.
        """
        ann = _get_tool_annotations("select")
        assert ann is not None, "select has no ToolAnnotations"
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False for select (form state changes on selection), got: {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    # -- read_text: destructiveHint -------------------------------------------

    def test_read_text_destructive_hint_is_false(self) -> None:
        """read_text is NOT destructive — it only reads visible text, no side-effects.

        destructiveHint must be explicitly False, not None.
        """
        ann = _get_tool_annotations("read_text")
        assert ann is not None, "read_text has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for read_text (pure read, no destructive side-effects), "
            f"got: {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )

    # -- snapshot: destructiveHint --------------------------------------------

    def test_snapshot_destructive_hint_is_false(self) -> None:
        """snapshot is NOT destructive — it captures page state without modifying anything.

        destructiveHint must be explicitly False, not None.
        """
        ann = _get_tool_annotations("snapshot")
        assert ann is not None, "snapshot has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for snapshot (read-only capture, no destructive side-effects), "
            f"got: {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )
