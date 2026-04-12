"""Failing RED-phase tests for #842: BrowserContentFetcher package export.

AC mapping (from task #842 — GREEN impl task, new AC beyond #841):

  AC-X1  serve/browser/src/owlbear_browser/__init__.py exports
          BrowserContentFetcher in __all__
  AC-X2  BrowserContentFetcher importable at package top-level
          (i.e. `from owlbear_browser import BrowserContentFetcher`)

All other #842 AC lines (BrowserContentFetcher/HttpxContentFetcher behaviour)
are already covered by test_contentfetcher_impl_830.py (RED partner #841).

Both tests below FAIL at RED phase:
  - AC-X1: AssertionError — 'BrowserContentFetcher' not in owlbear_browser.__all__
  - AC-X2: ImportError — cannot import name 'BrowserContentFetcher' from 'owlbear_browser'
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# TestFromAC_BrowserPackageExport
# ---------------------------------------------------------------------------


class TestFromAC_BrowserPackageExport:
    """AC-X1..X2: owlbear_browser package exports BrowserContentFetcher."""

    # --- AC-X1: __all__ membership ---

    def test_browser_package_all_includes_browsercontent_fetcher(self) -> None:
        """AC-X1: 'BrowserContentFetcher' is in owlbear_browser.__all__."""
        import owlbear_browser

        assert "BrowserContentFetcher" in owlbear_browser.__all__

    # --- AC-X2: top-level importable ---

    def test_browsercontent_fetcher_importable_from_browser_package(self) -> None:
        """AC-X2: `from owlbear_browser import BrowserContentFetcher` succeeds."""
        from owlbear_browser import BrowserContentFetcher  # type: ignore[attr-defined]  # noqa: F401
