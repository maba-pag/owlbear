"""RED-phase tests for #771: mcp-browser convention compliance.

AC coverage for items not addressed by test_mcp_browser_775.py (which covers
AC1-AC4: lifespan, env-var allowlist, navigate ToolError, tool exclusions).

  AC5 - All 6 tools have ToolAnnotations:
          navigate → idempotentHint=True
          select   → idempotentHint=True
          read_text → readOnlyHint=True
          snapshot  → readOnlyHint=True
          click     → readOnlyHint=False (state-changing)
          type      → readOnlyHint=False (state-changing)
  AC6 - __main__.py entry point exists and is importable
  AC7 - server.__all__ exports AppContext and app_lifespan

All tests MUST FAIL at RED phase:
  - No ToolAnnotations set on any tool  → annotations is None → AssertionError
  - __main__.py does not exist          → ModuleNotFoundError (ImportError)
  - __all__ missing AppContext/app_lifespan → AssertionError
"""

from __future__ import annotations

import importlib


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
# TestFromAC_ToolAnnotations — AC5: ToolAnnotations on all 6 tools
# ===========================================================================


class TestFromAC_ToolAnnotations:
    """All 6 browser tools must carry explicit ToolAnnotations (AC5)."""

    def test_all_six_tools_have_non_none_annotations(self) -> None:
        """Every registered tool must have a non-None annotations object."""
        from owlbear_mcp_browser.server import mcp_app

        missing = [
            t.name
            for t in mcp_app.list_tools()
            if getattr(t, "annotations", None) is None
        ]
        assert missing == [], f"Tools missing ToolAnnotations: {missing}"

    def test_navigate_has_idempotent_hint_true(self) -> None:
        """navigate() is idempotent — navigating to the same URL produces the same page (AC5)."""
        annotations = _get_tool_annotations("navigate")
        assert annotations is not None, "navigate has no ToolAnnotations; idempotentHint=True must be set"
        assert annotations.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for navigate, got: {annotations.idempotentHint!r}"  # type: ignore[union-attr]
        )

    def test_select_has_idempotent_hint_true(self) -> None:
        """select() is idempotent — selecting the same value in a dropdown is repeatable (AC5)."""
        annotations = _get_tool_annotations("select")
        assert annotations is not None, "select has no ToolAnnotations; idempotentHint=True must be set"
        assert annotations.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for select, got: {annotations.idempotentHint!r}"  # type: ignore[union-attr]
        )

    def test_read_text_has_read_only_hint_true(self) -> None:
        """read_text() is read-only — it reads page content without changing state (AC5)."""
        annotations = _get_tool_annotations("read_text")
        assert annotations is not None, "read_text has no ToolAnnotations; readOnlyHint=True must be set"
        assert annotations.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for read_text, got: {annotations.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    def test_snapshot_has_read_only_hint_true(self) -> None:
        """snapshot() is read-only — it captures page state without modifying it (AC5)."""
        annotations = _get_tool_annotations("snapshot")
        assert annotations is not None, "snapshot has no ToolAnnotations; readOnlyHint=True must be set"
        assert annotations.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for snapshot, got: {annotations.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    def test_click_is_not_read_only(self) -> None:
        """click() is not read-only — clicking an element changes page state (AC5)."""
        annotations = _get_tool_annotations("click")
        assert annotations is not None, "click has no ToolAnnotations; readOnlyHint=False must be set"
        assert annotations.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False for click, got: {annotations.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    def test_type_input_is_not_read_only(self) -> None:
        """'type' tool is not read-only — typing into a field changes page state (AC5)."""
        annotations = _get_tool_annotations("type")
        assert annotations is not None, "'type' tool has no ToolAnnotations; readOnlyHint=False must be set"
        assert annotations.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False for 'type', got: {annotations.readOnlyHint!r}"  # type: ignore[union-attr]
        )


# ===========================================================================
# TestFromAC_MainEntryPoint — AC6: __main__.py exists and is importable
# ===========================================================================


class TestFromAC_MainEntryPoint:
    """owlbear_mcp_browser.__main__ entry point must exist and be importable (AC6)."""

    def test_main_module_is_importable(self) -> None:
        """owlbear_mcp_browser.__main__ can be imported without error."""
        importlib.import_module("owlbear_mcp_browser.__main__")

    def test_main_module_references_mcp_server(self) -> None:
        """__main__ module contains an attribute that references the FastMCP server."""
        main = importlib.import_module("owlbear_mcp_browser.__main__")
        # __main__ must wire to _mcp (not mcp — that attr doesn't exist) per F4 guidance
        from owlbear_mcp_browser.server import _mcp as expected_server  # type: ignore[attr-defined]

        # main must reference the same server object (directly or via import)
        # Checking the module's namespace rather than any specific attribute name
        server_found = any(
            val is expected_server
            for name, val in vars(main).items()
            if not name.startswith("__")
        )
        assert server_found, "__main__ must import or reference the _mcp FastMCP server instance"


# ===========================================================================
# TestFromAC_PublicExports — AC7: __all__ exports AppContext and app_lifespan
# ===========================================================================


class TestFromAC_PublicExports:
    """server.__all__ must export AppContext and app_lifespan (AC7)."""

    def test_app_context_in_dunder_all(self) -> None:
        """AppContext must appear in owlbear_mcp_browser.server.__all__."""
        from owlbear_mcp_browser import server

        assert "AppContext" in server.__all__, (
            f"AppContext not in server.__all__: {server.__all__!r}"
        )

    def test_app_lifespan_in_dunder_all(self) -> None:
        """app_lifespan must appear in owlbear_mcp_browser.server.__all__."""
        from owlbear_mcp_browser import server

        assert "app_lifespan" in server.__all__, (
            f"app_lifespan not in server.__all__: {server.__all__!r}"
        )


