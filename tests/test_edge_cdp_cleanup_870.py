"""Failing tests for Edge/CDP code cleanup — #870.

All tests FAIL before cleanup (old code still present) and PASS after cleanup
(old modules deleted, error types removed, exports cleaned, test files gone).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent


class TestFromAC_EdgeCDPCleanup:
    """AC1-4: Old Edge/CDP modules, error types, exports, and test files removed."""

    # ── AC1: Source modules deleted ──────────────────────────────────────────

    def test_launcher_module_does_not_exist(self) -> None:
        """owlbear_browser.launcher (Edge-specific find_edge_binary etc.) must be deleted."""
        sys.modules.pop("owlbear_browser.launcher", None)
        with pytest.raises(ImportError):
            import owlbear_browser.launcher  # noqa: F401

    def test_edge_launcher_module_does_not_exist(self) -> None:
        """owlbear_browser.edge_launcher (EdgeCDPLauncher class) must be deleted."""
        sys.modules.pop("owlbear_browser.edge_launcher", None)
        with pytest.raises(ImportError):
            import owlbear_browser.edge_launcher  # noqa: F401

    def test_cdp_module_does_not_exist(self) -> None:
        """owlbear_browser.cdp (CDPConnectionManager, playwright_connect_over_cdp) must be deleted."""
        sys.modules.pop("owlbear_browser.cdp", None)
        with pytest.raises(ImportError):
            import owlbear_browser.cdp  # noqa: F401

    # ── AC2: Error types removed from _errors.py ─────────────────────────────

    def test_edge_not_found_error_removed_from_errors_module(self) -> None:
        """EdgeNotFoundError is no longer raised — must be deleted from _errors.py."""
        import owlbear_browser._errors as errors
        assert not hasattr(errors, "EdgeNotFoundError")

    def test_cdp_connection_error_removed_from_errors_module(self) -> None:
        """CDPConnectionError is no longer raised — must be deleted from _errors.py."""
        import owlbear_browser._errors as errors
        assert not hasattr(errors, "CDPConnectionError")

    # ── AC3: __init__.py exports cleaned ─────────────────────────────────────

    def test_init_no_edge_cdp_launcher_export(self) -> None:
        """EdgeCDPLauncher must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "EdgeCDPLauncher")

    def test_init_no_cdp_connection_manager_export(self) -> None:
        """CDPConnectionManager must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "CDPConnectionManager")

    def test_init_no_edge_not_found_error_export(self) -> None:
        """EdgeNotFoundError must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "EdgeNotFoundError")

    def test_init_no_cdp_connection_error_export(self) -> None:
        """CDPConnectionError must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "CDPConnectionError")

    def test_init_no_find_edge_binary_export(self) -> None:
        """find_edge_binary must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "find_edge_binary")

    def test_init_no_launch_edge_export(self) -> None:
        """launch_edge must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "launch_edge")

    def test_init_no_build_launch_args_export(self) -> None:
        """build_launch_args must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "build_launch_args")

    def test_init_no_resolve_edge_binary_export(self) -> None:
        """resolve_edge_binary alias (for find_edge_binary) must not be exported from the owlbear_browser package root."""
        import owlbear_browser
        assert not hasattr(owlbear_browser, "resolve_edge_binary")

    # ── AC4: Superseded test files deleted ───────────────────────────────────

    def test_edge_launcher_cdp_755_file_deleted(self) -> None:
        """tests/test_edge_launcher_cdp_755.py (21 Edge CDP tests) must be deleted."""
        assert not (_TESTS_DIR / "test_edge_launcher_cdp_755.py").exists()

    def test_edge_launcher_cdp_758_file_deleted(self) -> None:
        """tests/test_edge_launcher_cdp_758.py (Edge launcher + CDP implementation tests) must be deleted."""
        assert not (_TESTS_DIR / "test_edge_launcher_cdp_758.py").exists()

    def test_browser_package_scaffold_787_file_deleted(self) -> None:
        """tests/test_browser_package_scaffold_787.py (Edge launcher dep checks) must be deleted."""
        assert not (_TESTS_DIR / "test_browser_package_scaffold_787.py").exists()

    def test_browser_cdp_775_file_deleted(self) -> None:
        """tests/test_browser_cdp_775.py must be deleted."""
        assert not (_TESTS_DIR / "test_browser_cdp_775.py").exists()

    def test_mcp_browser_fetcher_852_file_deleted(self) -> None:
        """tests/test_mcp_browser_fetcher_852.py (Phase 1 fetcher tests) must be deleted."""
        assert not (_TESTS_DIR / "test_mcp_browser_fetcher_852.py").exists()

    def test_browser_package_class_removed_from_pipeline_775(self) -> None:
        """TestFromAC_BrowserPackage (13 Edge/CDP tests) must be removed from test_authenticated_content_pipeline_775.py.

        The 4 non-CDP classes (BrowserMCPServer, AuthWebRefreshHandler,
        ContentSafetyInversion, ReplaceOnChangeRefresh) must be retained.
        """
        content = (_TESTS_DIR / "test_authenticated_content_pipeline_775.py").read_text(encoding="utf-8")
        assert "class TestFromAC_BrowserPackage" not in content
