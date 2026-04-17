"""RED-phase tests for #857: Wire BrowserContentFetcher into MCP browser app_lifespan (AC2).

AC coverage:
  AC2 — app_lifespan() creates CDPConnectionManager + BrowserContentFetcher
         (guarded, fallback to None on failure).  CDPConnectionManager is
         disconnected in the finally block after yield.

Gap addressed: existing RED tests (test_mcp_browser_fetcher_852.py) cover AC1/AC3-AC6
via direct AppContext construction.  None test that app_lifespan() actually creates and
wires a BrowserContentFetcher into the yielded AppContext.

All tests MUST FAIL at RED phase:
  - current app_lifespan yields AppContext(cdp=..., page=...) with fetcher=None (default)
  - no call to BrowserContentFetcher() exists in app_lifespan at all
  => assertions on ctx.fetcher will be AssertionError / AttributeError
  => patch on owlbear_mcp_browser.server.BrowserContentFetcher raises AttributeError
     (the name is only TYPE_CHECKING-imported, not available at runtime yet)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_browser.server import app_lifespan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_launcher() -> MagicMock:
    """Return a MagicMock PlaywrightLauncher that launches and closes cleanly.

    Provides a mock BrowserContext via .context so the fetcher-wiring branch
    inside the lifespan can call BrowserContentFetcher(launcher.context).
    """
    page = MagicMock()
    page.close = AsyncMock()  # lifespan awaits page.close() in finally block
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    launcher = MagicMock()
    launcher.context = context
    launcher.launch = AsyncMock()
    launcher.close = AsyncMock()
    launcher.__aenter__ = AsyncMock(return_value=launcher)
    launcher.__aexit__ = AsyncMock(return_value=False)
    return launcher


# ===========================================================================
# TestFromAC_LifespanBrowserFetcherWiring — AC2
# ===========================================================================


class TestFromAC_LifespanBrowserFetcherWiring:
    """app_lifespan creates BrowserContentFetcher on successful PlaywrightLauncher.launch() (AC2).

    Updated for #871 Playwright pivot: CDPConnectionManager replaced by PlaywrightLauncher.
    """

    # ------------------------------------------------------------------
    # Happy-path: connect succeeds → fetcher is populated
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_not_none_when_cdp_connect_succeeds(self) -> None:
        """AC2: app_lifespan sets AppContext.fetcher to a non-None object on successful launch."""
        mock_launcher = _make_mock_launcher()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.fetcher is not None, (
                    "AppContext.fetcher must be set when PlaywrightLauncher launches successfully;"
                    " got None — app_lifespan is not creating BrowserContentFetcher"
                )

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_browser_content_fetcher_instance(self) -> None:
        """AC2: AppContext.fetcher is a BrowserContentFetcher after successful launch."""
        from owlbear_browser.fetcher import BrowserContentFetcher

        mock_launcher = _make_mock_launcher()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert isinstance(ctx.fetcher, BrowserContentFetcher), (
                    f"AppContext.fetcher must be a BrowserContentFetcher instance; got {type(ctx.fetcher)!r}"
                )

    # ------------------------------------------------------------------
    # Contract: BrowserContentFetcher constructed with the right CDPConnectionManager
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_browser_content_fetcher_constructed_with_cdp_manager(self) -> None:
        """AC2: BrowserContentFetcher is called with launcher.context (Playwright BrowserContext)."""
        mock_launcher = _make_mock_launcher()
        mock_fetcher_cls = MagicMock(return_value=MagicMock())

        with (
            patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher),
            patch("owlbear_mcp_browser.server.BrowserContentFetcher", mock_fetcher_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_fetcher_cls.assert_called_once_with(mock_launcher.context)

    # ------------------------------------------------------------------
    # Edge: each lifespan invocation creates an independent fetcher
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_creates_independent_fetcher_per_invocation(self) -> None:
        """AC2: Separate lifespan invocations each create a fresh BrowserContentFetcher."""
        mock_launcher = _make_mock_launcher()
        fetcher1: object | None = None
        fetcher2: object | None = None

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx1:
                fetcher1 = ctx1.fetcher
            async with app_lifespan(MagicMock()) as ctx2:
                fetcher2 = ctx2.fetcher

        assert fetcher1 is not None, "First lifespan invocation must provide a non-None fetcher"
        assert fetcher2 is not None, "Second lifespan invocation must provide a non-None fetcher"
        assert fetcher1 is not fetcher2, "Each lifespan invocation must create an independent BrowserContentFetcher"


# ===========================================================================
# TestBuilderDiscovered — gaps identified in code review
# ===========================================================================


class TestBuilderDiscovered:
    """Builder-discovered tests — fill gaps identified in #857 code review.

    Covers:
    - AC2 guard: fetcher=None when PlaywrightLauncher.launch() raises
    - AC3: navigate calls fetcher.fetch(url), stores result, returns markdown
    - AC4: AuthenticationRequired is wrapped into ToolError
    - AC5: navigate raises ToolError unconditionally when fetcher is None
    """

    # ------------------------------------------------------------------
    # AC2 guard: failed launch → fetcher stays None
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_none_when_launcher_launch_raises(self) -> None:
        """AC2 guard: app_lifespan sets fetcher=None when PlaywrightLauncher.launch() raises."""
        mock_launcher = MagicMock()
        mock_launcher.launch = AsyncMock(side_effect=Exception("browser unavailable"))
        mock_launcher.close = AsyncMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.fetcher is None, (
                    f"fetcher must be None when PlaywrightLauncher.launch() raises; got {ctx.fetcher!r}"
                )

    # ------------------------------------------------------------------
    # AC3: navigate calls fetcher.fetch(url), stores last_content, returns it
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_navigate_calls_fetcher_fetch_with_exact_url(self) -> None:
        """AC3: navigate() calls fetcher.fetch(url) with the exact URL argument."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext, navigate

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value="# Page")
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["corp.example.com"]),
            fetcher=mock_fetcher,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        await navigate(ctx, url="https://corp.example.com/page")

        mock_fetcher.fetch.assert_called_once_with("https://corp.example.com/page")

    @pytest.mark.asyncio
    async def test_navigate_stores_fetched_content_in_last_content(self) -> None:
        """AC3: navigate() stores the fetcher result in app_ctx.last_content."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext, navigate

        fetched = "# My Page\n\nBody text."
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=fetched)
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["corp.example.com"]),
            fetcher=mock_fetcher,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        await navigate(ctx, url="https://corp.example.com/report")

        assert app_ctx.last_content == fetched, f"last_content must equal fetched content; got {app_ctx.last_content!r}"

    @pytest.mark.asyncio
    async def test_navigate_returns_fetched_markdown_content(self) -> None:
        """AC3: navigate() returns the markdown string returned by fetcher.fetch()."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext, navigate

        fetched = "# Title\n\nParagraph."
        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value=fetched)
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["corp.example.com"]),
            fetcher=mock_fetcher,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await navigate(ctx, url="https://corp.example.com/doc")

        assert result == fetched, f"navigate must return fetched markdown; got {result!r}"

    # ------------------------------------------------------------------
    # AC4: AuthenticationRequired → ToolError with descriptive message
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_navigate_authentication_required_raises_tool_error_with_descriptive_message(
        self,
    ) -> None:
        """AC4: navigate() wraps AuthenticationRequired into ToolError with a descriptive message."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext, navigate

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(side_effect=AuthenticationRequired("login page detected"))
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["sso.corp.com"]),
            fetcher=mock_fetcher,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        with pytest.raises(ToolError, match=r"SSO|authentication|session"):
            await navigate(ctx, url="https://sso.corp.com/protected")

    # ------------------------------------------------------------------
    # Adjudicated in #877: fetcher=None, page=None → dry-run return url
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_navigate_fetcher_none_returns_url_when_page_none(self) -> None:
        """Adjudicated in #877: navigate() returns url (dry-run) when fetcher=None and page=None."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext, navigate

        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["corp.example.com"]),
            fetcher=None,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await navigate(ctx, url="https://corp.example.com/page")
        assert result == "https://corp.example.com/page"

    @pytest.mark.asyncio
    async def test_navigate_fetcher_none_falls_back_to_page_goto_when_page_is_set(self) -> None:
        """AC5 fallback: navigate() calls page.goto(url) when fetcher is None but page is set."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext, navigate

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["corp.example.com"]),
            fetcher=None,
            page=mock_page,
        )
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        result = await navigate(ctx, url="https://corp.example.com/page")

        mock_page.goto.assert_called_once_with("https://corp.example.com/page")
        assert result == "https://corp.example.com/page"
