"""RED-phase tests for #852: Wire BrowserContentFetcher into MCP browser navigate/read_text.

AC coverage:
  AC1 — AppContext holds fetcher: BrowserContentFetcher | None (default None)
         and last_content: str (default "").
  AC2 — navigate(ctx, url) calls fetcher.fetch(url), stores result in last_content,
         returns the fetched markdown content.
  AC3 — If AuthenticationRequired is raised during navigate(), it is caught and
         converted to a ToolError with a descriptive message.
  AC4 — read_text(ctx) returns last_content from AppContext (empty string if no prior navigate).
  AC5 — Integration: stub BrowserContentFetcher, call navigate, verify delegation and
         error handling for both success and AuthenticationRequired cases.

All tests MUST FAIL at RED phase:
  - AppContext lacks fetcher and last_content fields → TypeError / AttributeError
  - navigate() has no ctx parameter and no fetcher delegation → TypeError / AssertionError
  - read_text() has no ctx parameter and returns "" without AppContext state → TypeError / AssertionError
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_mcp_browser.allowlist import DomainAllowlist
from owlbear_mcp_browser.server import AppContext

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_URL = "https://contoso.sharepoint.com/sites/team"
_MARKDOWN_CONTENT = "# Project Home\n\nMeeting notes paragraph."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_fetcher(return_value: str = _MARKDOWN_CONTENT) -> MagicMock:
    """Return a mock BrowserContentFetcher whose fetch() coroutine returns return_value."""
    fetcher = MagicMock()
    fetcher.fetch = AsyncMock(return_value=return_value)
    return fetcher


def _make_app_ctx(
    domains: list[str],
    fetcher: object = None,
    last_content: str = "",
) -> AppContext:
    """Return an AppContext with BrowserContentFetcher wiring fields set."""
    return AppContext(
        allowlist=DomainAllowlist(domains=domains),
        fetcher=fetcher,
        last_content=last_content,
    )


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a MagicMock ctx with app_ctx wired into lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


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


# ===========================================================================
# TestFromAC_NavigateFetcherWiring — AC2/AC3: navigate delegates to fetcher
# ===========================================================================


class TestFromAC_NavigateFetcherWiring:
    """navigate(ctx, url) delegates to BrowserContentFetcher and handles errors (AC2/AC3)."""

    @pytest.mark.asyncio
    async def test_navigate_calls_fetcher_fetch_with_url(self) -> None:
        """AC2: navigate() calls fetcher.fetch(url) exactly once with the given URL."""
        from owlbear_mcp_browser.server import navigate

        mock_fetcher = _make_mock_fetcher()
        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=mock_fetcher))

        await navigate(ctx, _ALLOWED_URL)

        mock_fetcher.fetch.assert_called_once_with(_ALLOWED_URL)

    @pytest.mark.asyncio
    async def test_navigate_returns_markdown_from_fetcher(self) -> None:
        """AC2: navigate() returns the markdown string returned by fetcher.fetch()."""
        from owlbear_mcp_browser.server import navigate

        mock_fetcher = _make_mock_fetcher(return_value=_MARKDOWN_CONTENT)
        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=mock_fetcher))

        result = await navigate(ctx, _ALLOWED_URL)

        assert result == _MARKDOWN_CONTENT

    @pytest.mark.asyncio
    async def test_navigate_stores_result_in_last_content(self) -> None:
        """AC2: navigate() stores the fetched content in AppContext.last_content."""
        from owlbear_mcp_browser.server import navigate

        mock_fetcher = _make_mock_fetcher(return_value=_MARKDOWN_CONTENT)
        app_ctx = _make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=mock_fetcher)
        ctx = _make_mcp_ctx(app_ctx)

        await navigate(ctx, _ALLOWED_URL)

        assert app_ctx.last_content == _MARKDOWN_CONTENT

    @pytest.mark.asyncio
    async def test_navigate_authentication_required_raises_tool_error(self) -> None:
        """AC3: AuthenticationRequired from fetcher.fetch() is caught and raised as ToolError."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_mcp_browser.server import navigate

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=AuthenticationRequired("SSO redirect detected"))
        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=mock_fetcher))

        with pytest.raises(ToolError):
            await navigate(ctx, _ALLOWED_URL)

    @pytest.mark.asyncio
    async def test_navigate_tool_error_message_describes_sso_expiry(self) -> None:
        """AC3: The ToolError message is descriptive — contains 'SSO' or 'session' or 'expired'."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_mcp_browser.server import navigate

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=AuthenticationRequired("SSO redirect detected"))
        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=mock_fetcher))

        with pytest.raises(ToolError) as exc_info:
            await navigate(ctx, _ALLOWED_URL)

        message = str(exc_info.value).lower()
        assert any(token in message for token in ("sso", "session", "expired", "authentication")), (
            f"ToolError message should describe SSO/auth expiry, got: {exc_info.value!r}"
        )

    @pytest.mark.asyncio
    async def test_navigate_fetcher_none_raises_tool_error(self) -> None:
        """AC3-related: navigate() raises ToolError when AppContext.fetcher is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        # fetcher=None — browser not initialised
        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=None))

        with pytest.raises(ToolError):
            await navigate(ctx, _ALLOWED_URL)

    @pytest.mark.asyncio
    async def test_navigate_fetcher_none_tool_error_describes_unavailability(self) -> None:
        """navigate() ToolError when fetcher is None contains 'browser' or 'available'."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=None))

        with pytest.raises(ToolError) as exc_info:
            await navigate(ctx, _ALLOWED_URL)

        message = str(exc_info.value).lower()
        assert any(token in message for token in ("browser", "available", "not")), (
            f"ToolError should describe browser unavailability, got: {exc_info.value!r}"
        )


# ===========================================================================
# TestFromAC_ReadTextState — AC4: read_text returns AppContext.last_content
# ===========================================================================


class TestFromAC_ReadTextState:
    """read_text(ctx) returns last_content from AppContext; empty string before any navigate (AC4)."""

    @pytest.mark.asyncio
    async def test_read_text_returns_last_content_after_navigate(self) -> None:
        """AC4: read_text(ctx) returns the content stored by the most recent navigate()."""
        from owlbear_mcp_browser.server import navigate, read_text

        mock_fetcher = _make_mock_fetcher(return_value=_MARKDOWN_CONTENT)
        app_ctx = _make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=mock_fetcher)
        ctx = _make_mcp_ctx(app_ctx)

        await navigate(ctx, _ALLOWED_URL)
        result = await read_text(ctx)

        assert result == _MARKDOWN_CONTENT

    @pytest.mark.asyncio
    async def test_read_text_returns_empty_string_before_navigate(self) -> None:
        """AC4: read_text(ctx) returns empty string when no navigate has been called."""
        from owlbear_mcp_browser.server import read_text

        app_ctx = _make_app_ctx(domains=[], fetcher=None)
        ctx = _make_mcp_ctx(app_ctx)

        result = await read_text(ctx)

        assert result == ""

    @pytest.mark.asyncio
    async def test_read_text_returns_most_recent_navigate_content(self) -> None:
        """AC4: read_text(ctx) returns the LAST navigate content when called multiple times."""
        from owlbear_mcp_browser.server import navigate, read_text

        first_content = "# First Page"
        second_content = "# Second Page"
        fetcher = MagicMock()
        fetcher.fetch = AsyncMock(side_effect=[first_content, second_content])
        app_ctx = _make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=fetcher)
        ctx = _make_mcp_ctx(app_ctx)

        await navigate(ctx, "https://contoso.sharepoint.com/first")
        await navigate(ctx, "https://contoso.sharepoint.com/second")
        result = await read_text(ctx)

        assert result == second_content


# ===========================================================================
# TestFromAC_IntegrationFetcherWiring — AC5: integration stub tests
# ===========================================================================


class TestFromAC_IntegrationFetcherWiring:
    """Integration: stub BrowserContentFetcher wired via AppContext (AC5)."""

    @pytest.mark.asyncio
    async def test_integration_navigate_success_delegation(self) -> None:
        """AC5: Stubbed fetcher receives fetch(url) call and its return flows through navigate()."""
        from owlbear_mcp_browser.server import navigate

        stub_fetcher = _make_mock_fetcher(return_value=_MARKDOWN_CONTENT)
        app_ctx = _make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=stub_fetcher)
        ctx = _make_mcp_ctx(app_ctx)

        result = await navigate(ctx, _ALLOWED_URL)

        stub_fetcher.fetch.assert_called_once_with(_ALLOWED_URL)
        assert result == _MARKDOWN_CONTENT
        assert app_ctx.last_content == _MARKDOWN_CONTENT

    @pytest.mark.asyncio
    async def test_integration_navigate_authentication_required_error_handling(self) -> None:
        """AC5: AuthenticationRequired from stub fetcher is surfaced as ToolError, not propagated raw."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_mcp_browser.server import navigate

        stub_fetcher = MagicMock()
        stub_fetcher.fetch = AsyncMock(side_effect=AuthenticationRequired("login page"))
        app_ctx = _make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=stub_fetcher)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await navigate(ctx, _ALLOWED_URL)

        # AuthenticationRequired must NOT propagate unwrapped
        # (the outer pytest.raises(ToolError) already asserts this)

    @pytest.mark.asyncio
    async def test_integration_authentication_required_not_raised_as_raw_exception(self) -> None:
        """AC5: Raw AuthenticationRequired must never escape navigate() — only ToolError is raised."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_mcp_browser.server import navigate

        stub_fetcher = MagicMock()
        stub_fetcher.fetch = AsyncMock(side_effect=AuthenticationRequired("login"))
        ctx = _make_mcp_ctx(_make_app_ctx(domains=["contoso.sharepoint.com"], fetcher=stub_fetcher))

        exc = None
        try:
            await navigate(ctx, _ALLOWED_URL)
        except ToolError as e:
            exc = e
        except AuthenticationRequired:
            pytest.fail("AuthenticationRequired escaped navigate() — must be wrapped in ToolError")

        assert exc is not None, "navigate() should have raised ToolError"
