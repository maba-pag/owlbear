"""Tests for #853: mcp-browser session management (Playwright launcher model).

Task is tagged ``archived`` + ``superseded`` (CDP approach blocked by Group Policy; parent
#837 pivoted to Playwright ``launch_persistent_context()`` + SSO extension).  Test file was
updated by tasks #871 (Playwright pivot) and #877 (AC11 adjudication).  All 27 tests PASS
on current HEAD.

AC coverage:
  AC1  AppContext includes PlaywrightLauncher and optional Page fields (defaults None)
  AC2  lifespan: successful PlaywrightLauncher.launch() yields AppContext with launcher+page
  AC3  lifespan: failed PlaywrightLauncher.launch() yields AppContext with launcher=None, page=None
  AC4  lifespan cleanup: calls page.close() and launcher.close() on exit; skipped when launch failed
  AC5  navigate(): checks allowlist then calls page.goto(url)
  AC6  click(): calls page.locator(selector).click()
  AC7  type(): calls page.locator(selector).fill(text)
  AC8  select(): calls page.locator(selector).select_option(value)
  AC9  read_text(): calls extract_content(page.content(), page.url)
  AC10 snapshot(): calls page.aria_snapshot()
  AC11 (adjudicated #877): click/type/select raise ToolError when page is None;
       navigate returns url (dry-run), read_text/snapshot return last_content string
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_URL = "https://sharepoint.example.com/sites/team"
_BLOCKED_URL = "https://evil.example.net/malware"
_SAMPLE_HTML = "<html><body><h1>Hello</h1><p>World.</p></body></html>"
_SAMPLE_MARKDOWN = "# Hello\n\nWorld."
_SELECTOR = "#submit-button"
_TEXT_INPUT = "test@example.com"
_OPTION_VALUE = "option-a"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_locator() -> MagicMock:
    """Return a mock Playwright locator with async action methods."""
    loc = MagicMock()
    loc.click = AsyncMock()
    loc.fill = AsyncMock()
    loc.select_option = AsyncMock()
    return loc


def _make_mock_page() -> MagicMock:
    """Return a mock Playwright Page with all tool-facing async methods."""
    page = MagicMock()
    page.url = _ALLOWED_URL
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=_SAMPLE_HTML)
    page.close = AsyncMock()
    loc = _make_mock_locator()
    loc.aria_snapshot = AsyncMock(return_value="# Snapshot\n- item 1")
    page.locator = MagicMock(return_value=loc)
    return page


def _make_mock_launcher(page: MagicMock) -> MagicMock:
    """Return a mock PlaywrightLauncher wired with a BrowserContext and page."""
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    launcher = MagicMock()
    launcher.context = context
    launcher.launch = AsyncMock()
    launcher.close = AsyncMock()
    launcher.__aenter__ = AsyncMock(return_value=launcher)
    launcher.__aexit__ = AsyncMock(return_value=False)
    return launcher


def _make_mcp_ctx_with_page(page: MagicMock) -> MagicMock:
    """Return a mock MCP ctx whose lifespan_context has launcher and page set."""
    from owlbear_mcp_browser.allowlist import DomainAllowlist
    from owlbear_mcp_browser.server import AppContext

    app_ctx = AppContext(
        allowlist=DomainAllowlist(domains=["sharepoint.example.com"]),
        launcher=MagicMock(),
        page=page,
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_mcp_ctx_no_page() -> MagicMock:
    """Return a mock MCP ctx whose lifespan_context has page=None (no browser session)."""
    from owlbear_mcp_browser.allowlist import DomainAllowlist
    from owlbear_mcp_browser.server import AppContext

    app_ctx = AppContext(
        allowlist=DomainAllowlist(domains=["sharepoint.example.com"]),
        launcher=None,
        page=None,
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_AppContextFields — AC1
# ===========================================================================


class TestFromAC_AppContextFields:
    """AC1: AppContext dataclass must expose launcher and page as optional fields (updated #871)."""

    def test_appcontext_cdp_defaults_to_none(self) -> None:
        """AppContext constructed with only allowlist must have launcher=None by default."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert ctx.launcher is None

    def test_appcontext_page_defaults_to_none(self) -> None:
        """AppContext constructed with only allowlist must have page=None by default."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert ctx.page is None

    def test_appcontext_accepts_cdp_kwarg(self) -> None:
        """AppContext constructor must accept launcher keyword argument and store it."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        mock_launcher = MagicMock()
        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), launcher=mock_launcher)
        assert ctx.launcher is mock_launcher

    def test_appcontext_accepts_page_kwarg(self) -> None:
        """AppContext constructor must accept page keyword argument and store it."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        mock_page = MagicMock()
        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        assert ctx.page is mock_page


# ===========================================================================
# TestFromAC_LifespanSuccessfulConnection — AC2
# ===========================================================================


class TestFromAC_LifespanSuccessfulConnection:
    """AC2: Successful PlaywrightLauncher start yields AppContext with launcher and page (updated #871)."""

    @pytest.mark.asyncio
    async def test_lifespan_sets_cdp_on_successful_connect(self) -> None:
        """Successful launch: AppContext.launcher is set to the PlaywrightLauncher instance."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.launcher is mock_launcher

    @pytest.mark.asyncio
    async def test_lifespan_sets_page_on_successful_connect(self) -> None:
        """Successful launch: AppContext.page is set from launcher.context.new_page()."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.page is mock_page

    @pytest.mark.asyncio
    async def test_lifespan_calls_cdp_connect(self) -> None:
        """App lifespan calls PlaywrightLauncher.launch() during startup."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(mock_server) as _:
                pass

        mock_launcher.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_calls_new_page(self) -> None:
        """App lifespan calls launcher.context.new_page() to get the shared page."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(mock_server) as _:
                pass

        mock_launcher.context.new_page.assert_called_once()


# ===========================================================================
# TestFromAC_LifespanFailedConnection — AC3
# ===========================================================================


class TestFromAC_LifespanFailedConnection:
    """AC3: When PlaywrightLauncher.launch() raises, lifespan yields launcher=None, page=None."""

    @pytest.mark.asyncio
    async def test_lifespan_sets_cdp_none_on_failed_connect(self) -> None:
        """ctx.launcher is None when launch raises (Playwright unavailable)."""
        from owlbear_mcp_browser.server import app_lifespan

        failing_launcher = MagicMock()
        failing_launcher.launch = AsyncMock(side_effect=RuntimeError("playwright unavailable"))
        failing_launcher.close = AsyncMock()
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=failing_launcher):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.launcher is None

    @pytest.mark.asyncio
    async def test_lifespan_sets_page_none_on_failed_connect(self) -> None:
        """ctx.page is None when launch raises (Playwright unavailable)."""
        from owlbear_mcp_browser.server import app_lifespan

        failing_launcher = MagicMock()
        failing_launcher.launch = AsyncMock(side_effect=RuntimeError("playwright unavailable"))
        failing_launcher.close = AsyncMock()
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=failing_launcher):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.page is None


# ===========================================================================
# TestFromAC_LifespanCleanup — AC4
# ===========================================================================


class TestFromAC_LifespanCleanup:
    """AC4: Lifespan finally-block closes page and launcher on exit (updated for #871)."""

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_closes_page(self) -> None:
        """App lifespan calls page.close() after yielding (cleanup on session end)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(mock_server) as _:
                pass

        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_disconnects_cdp(self) -> None:
        """App lifespan calls launcher.close() after yielding (cleanup on session end)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(mock_server) as _:
                pass

        mock_launcher.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_skipped_when_connect_failed(self) -> None:
        """When launch failed (launcher=None), lifespan exits without calling close."""
        from owlbear_mcp_browser.server import app_lifespan

        failing_launcher = MagicMock()
        failing_launcher.launch = AsyncMock(side_effect=Exception("no browser"))
        failing_launcher.close = AsyncMock()
        mock_server = MagicMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=failing_launcher):
            async with app_lifespan(mock_server) as _:
                pass

        failing_launcher.close.assert_not_called()


# ===========================================================================
# TestFromAC_NavigateToolBody — AC5
# ===========================================================================


class TestFromAC_NavigateToolBody:
    """AC5: navigate() checks allowlist via ctx then delegates to page.goto(url)."""

    @pytest.mark.asyncio
    async def test_navigate_calls_page_goto_with_allowed_url(self) -> None:
        """navigate(ctx, url) calls page.goto(url) when domain is in allowlist."""
        from owlbear_mcp_browser.server import navigate

        mock_page = _make_mock_page()
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        await navigate(ctx, _ALLOWED_URL)  # FAILS: navigate has no ctx param

        mock_page.goto.assert_called_once_with(_ALLOWED_URL)

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_for_blocked_domain(self) -> None:
        """navigate(ctx, url) raises ToolError when domain is not in ctx allowlist."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        mock_page = _make_mock_page()
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await navigate(ctx, _BLOCKED_URL)  # FAILS: navigate has no ctx param

    @pytest.mark.asyncio
    async def test_navigate_does_not_call_goto_when_blocked(self) -> None:
        """navigate does not call page.goto when the domain is blocked (allowlist check first)."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        mock_page = _make_mock_page()
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await navigate(ctx, _BLOCKED_URL)  # FAILS: navigate has no ctx param

        mock_page.goto.assert_not_called()


# ===========================================================================
# TestFromAC_ClickToolBody — AC6
# ===========================================================================


class TestFromAC_ClickToolBody:
    """AC6: click() delegates to page.locator(selector).click()."""

    @pytest.mark.asyncio
    async def test_click_calls_locator_click(self) -> None:
        """click(ctx, selector) calls page.locator(selector).click()."""
        from owlbear_mcp_browser.server import click

        mock_page = _make_mock_page()
        locator_mock = mock_page.locator.return_value
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        await click(ctx, _SELECTOR)  # FAILS: click has no ctx param

        mock_page.locator.assert_called_once_with(_SELECTOR)
        locator_mock.click.assert_called_once()


# ===========================================================================
# TestFromAC_TypeToolBody — AC7
# ===========================================================================


class TestFromAC_TypeToolBody:
    """AC7: type() delegates to page.locator(selector).fill(text)."""

    @pytest.mark.asyncio
    async def test_type_calls_locator_fill(self) -> None:
        """type_input(ctx, selector, text) calls page.locator(selector).fill(text)."""
        from owlbear_mcp_browser.server import type_input

        mock_page = _make_mock_page()
        locator_mock = mock_page.locator.return_value
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        await type_input(ctx, _SELECTOR, _TEXT_INPUT)  # FAILS: type_input has no ctx param

        mock_page.locator.assert_called_once_with(_SELECTOR)
        locator_mock.fill.assert_called_once_with(_TEXT_INPUT)


# ===========================================================================
# TestFromAC_SelectToolBody — AC8
# ===========================================================================


class TestFromAC_SelectToolBody:
    """AC8: select() delegates to page.locator(selector).select_option(value)."""

    @pytest.mark.asyncio
    async def test_select_calls_locator_select_option(self) -> None:
        """select(ctx, selector, value) calls page.locator(selector).select_option(value)."""
        from owlbear_mcp_browser.server import select

        mock_page = _make_mock_page()
        locator_mock = mock_page.locator.return_value
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        await select(ctx, _SELECTOR, _OPTION_VALUE)  # FAILS: select has no ctx param

        mock_page.locator.assert_called_once_with(_SELECTOR)
        locator_mock.select_option.assert_called_once_with(_OPTION_VALUE)


# ===========================================================================
# TestFromAC_ReadTextToolBody — AC9
# ===========================================================================


class TestFromAC_ReadTextToolBody:
    """AC9: read_text() calls extract_content(await page.content(), page.url)."""

    @pytest.mark.asyncio
    async def test_read_text_calls_extract_content_with_page_html_and_url(self) -> None:
        """read_text(ctx) calls extract_content with page HTML and page.url; returns result."""
        from owlbear_mcp_browser.server import read_text

        mock_page = _make_mock_page()
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        # FAILS: extract_content not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.extract_content", return_value=_SAMPLE_MARKDOWN) as mock_extract:
            result = await read_text(ctx)  # FAILS: read_text has no ctx param

        mock_page.content.assert_called_once()
        mock_extract.assert_called_once_with(_SAMPLE_HTML, mock_page.url)
        assert result == _SAMPLE_MARKDOWN


# ===========================================================================
# TestFromAC_SnapshotToolBody — AC10
# ===========================================================================


class TestFromAC_SnapshotToolBody:
    """AC10: snapshot() delegates to page.aria_snapshot()."""

    @pytest.mark.asyncio
    async def test_snapshot_calls_aria_snapshot(self) -> None:
        """snapshot(ctx) calls page.aria_snapshot() and returns its result."""
        from owlbear_mcp_browser.server import snapshot

        mock_page = _make_mock_page()
        ctx = _make_mcp_ctx_with_page(mock_page)  # FAILS: AppContext lacks cdp/page

        result = await snapshot(ctx)  # FAILS: snapshot has no ctx param

        mock_page.locator("body").aria_snapshot.assert_called_once()
        assert result == "# Snapshot\n- item 1"


# ===========================================================================
# TestFromAC_ToolErrorWhenNoPage — AC11
# ===========================================================================


class TestFromAC_ToolErrorWhenNoPage:
    """AC11: Every tool raises ToolError when ctx.lifespan_context.page is None."""

    @pytest.mark.asyncio
    async def test_navigate_returns_url_when_page_none(self) -> None:
        """navigate returns url (dry-run) when AppContext page is None and domain is allowed.

        Adjudicated in #877: AppContext with fetcher=None and page=None should return the
        url (dry-run path) rather than raising ToolError. Allowlist check still enforced.
        """
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx_no_page()

        # FAILS on HEAD: navigate still raises ToolError instead of returning url
        result = await navigate(ctx, _ALLOWED_URL)
        assert result == _ALLOWED_URL

    @pytest.mark.asyncio
    async def test_click_raises_when_page_none(self) -> None:
        """click raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import click

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await click(ctx, _SELECTOR)  # FAILS: click has no ctx param + no page check

    @pytest.mark.asyncio
    async def test_type_raises_when_page_none(self) -> None:
        """type_input raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import type_input

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await type_input(ctx, _SELECTOR, _TEXT_INPUT)  # FAILS: no ctx param + no page check

    @pytest.mark.asyncio
    async def test_select_raises_when_page_none(self) -> None:
        """select raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import select

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await select(ctx, _SELECTOR, _OPTION_VALUE)  # FAILS: no ctx param + no page check

    @pytest.mark.asyncio
    async def test_read_text_returns_string_when_page_none(self) -> None:
        """read_text returns last_content fallback (empty string) when page is None.

        Adjudicated in #877: read_text supports fetcher-only pipeline and should not
        raise ToolError when page is None — return last_content instead.
        """
        from owlbear_mcp_browser.server import read_text

        ctx = _make_mcp_ctx_no_page()

        # FAILS on HEAD: read_text still raises ToolError instead of returning last_content
        result = await read_text(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_snapshot_returns_string_when_page_none(self) -> None:
        """snapshot returns last_content fallback (empty string) when page is None.

        Adjudicated in #877: snapshot supports fetcher-only pipeline and should not
        raise ToolError when page is None — return last_content instead.
        """
        from owlbear_mcp_browser.server import snapshot

        ctx = _make_mcp_ctx_no_page()

        # FAILS on HEAD: snapshot still raises ToolError instead of returning last_content
        result = await snapshot(ctx)
        assert isinstance(result, str)
