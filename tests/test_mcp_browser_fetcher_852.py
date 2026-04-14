"""Retained tests for #852: AppContext fetcher/last_content field contracts.

AC coverage:
  AC1 — AppContext holds fetcher: BrowserContentFetcher | None (default None)
         and last_content: str (default "").

Tests for AC2–AC5 (fetcher delegation, AuthenticationRequired, last_content caching,
integration) were removed by #859: they asserted Phase 1 behavior superseded by the
Playwright/CDP approach. Phase 2 coverage lives in test_mcp_browser_session_837.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from owlbear_mcp_browser.allowlist import DomainAllowlist
from owlbear_mcp_browser.server import AppContext

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MARKDOWN_CONTENT = "# Project Home\n\nMeeting notes paragraph."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_fetcher(return_value: str = _MARKDOWN_CONTENT) -> MagicMock:
    """Return a mock BrowserContentFetcher whose fetch() coroutine returns return_value."""
    fetcher = MagicMock()
    fetcher.fetch = AsyncMock(return_value=return_value)
    return fetcher


# ===========================================================================
# TestFromAC_AppContextFields — AC1: AppContext holds fetcher and last_content
# ===========================================================================


class TestFromAC_AppContextFields:
    """AppContext dataclass has fetcher and last_content fields with correct defaults (AC1)."""

    def test_app_ctx_has_fetcher_field_default_none(self) -> None:
        """AppContext.fetcher defaults to None when not supplied."""
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert app_ctx.fetcher is None

    def test_app_ctx_has_last_content_field_default_empty_string(self) -> None:
        """AppContext.last_content defaults to empty string when not supplied."""
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert app_ctx.last_content == ""

    def test_app_ctx_accepts_fetcher_kwarg(self) -> None:
        """AppContext can be constructed with fetcher=<mock> without TypeError."""
        mock_fetcher = _make_mock_fetcher()
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), fetcher=mock_fetcher)
        assert app_ctx.fetcher is mock_fetcher

    def test_app_ctx_accepts_last_content_kwarg(self) -> None:
        """AppContext can be constructed with last_content='...' without TypeError."""
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=[]),
            last_content="some prior content",
        )
        assert app_ctx.last_content == "some prior content"
