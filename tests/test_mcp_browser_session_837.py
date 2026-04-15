"""Failing RED-phase tests for #837: browser session management in mcp-browser AppContext.

AC coverage:
  AC1  AppContext includes CDPConnectionManager and optional Page fields
  AC2  Lifespan opens CDP connection to running Edge, or degrades gracefully
         (cdp=None, page=None) when CDPConnectionError is raised
  AC3  Lifespan cleanup disconnects CDP and closes browser on exit —
         whether exit is clean or via exception
  AC4  navigate() checks allowlist *then* calls page.goto(url)
  AC5  click() calls page.locator(selector).click()
  AC6  type_input() calls page.locator(selector).fill(text)
  AC7  select() calls page.locator(selector).select_option(value)
  AC8  read_text() calls extract_content(page.content(), page.url) and returns result
  AC9  snapshot() calls page.aria_snapshot() and returns result as markdown
  AC10 All 6 tools raise ToolError when page is None (no active session)

All 22 tests MUST FAIL on current HEAD:
  - AppContext has no cdp/page fields       → AttributeError / AssertionError (AC1 tests)
  - app_lifespan does not import/use CDP    → AssertionError on ctx.cdp/page (AC2/AC3 tests)
  - Tools have no ctx parameter             → TypeError when called with ctx (AC4-AC10 tests)
  - Tool stubs do not use Page at all       → mock assertions fail after #850 adds ctx
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_page() -> MagicMock:
    """Return a MagicMock Playwright Page with the async methods used by server tools."""
    page = MagicMock()
    page.url = "https://example.com/page"
    page.goto = AsyncMock()
    page.close = AsyncMock()
    page.content = AsyncMock(return_value="<html><body><h1>Hello</h1></body></html>")
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.select_option = AsyncMock()
    locator.aria_snapshot = AsyncMock(return_value="- heading 'Hello' [level=1]")
    page.locator = MagicMock(return_value=locator)
    return page


def _make_mock_browser(page: MagicMock) -> MagicMock:
    """Return a MagicMock Playwright Browser with one context/page, patched at CDP boundary."""
    mock_ctx = MagicMock()
    mock_ctx.pages = [page]
    mock_ctx.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.contexts = [mock_ctx]
    browser.close = AsyncMock()
    return browser


def _make_mock_launcher(page: MagicMock) -> MagicMock:
    """Return a mock PlaywrightLauncher with a context that provides the given page."""
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    launcher = MagicMock()
    launcher.context = context
    launcher.launch = AsyncMock()
    launcher.close = AsyncMock()
    launcher.__aenter__ = AsyncMock(return_value=launcher)
    launcher.__aexit__ = AsyncMock(return_value=False)
    return launcher


def _make_ctx_with_page(
    page: MagicMock | None,
    *,
    launcher: MagicMock | None = None,
    allowed_domains: list[str] | None = None,
) -> MagicMock:
    """Return a mock MCP Context whose lifespan_context exposes page, launcher, and allowlist.

    Uses SimpleNamespace so the test does not depend on AppContext having specific fields —
    the tool implementation is what is under test, not the dataclass construction.
    """
    from owlbear_mcp_browser.allowlist import DomainAllowlist

    domains: list[str] = allowed_domains if allowed_domains is not None else ["example.com"]
    lc = SimpleNamespace(
        allowlist=DomainAllowlist(domains=domains),
        launcher=launcher,
        page=page,
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = lc
    return ctx


# ===========================================================================
# TestFromAC_AppContextFields — AC1: AppContext dataclass has cdp + page fields
# ===========================================================================


class TestFromAC_AppContextFields:
    """AppContext must declare CDPConnectionManager and optional Page fields (AC1)."""

    def test_appcontext_has_cdp_field(self) -> None:
        """AppContext dataclass must have a 'launcher' field (updated for #871 Playwright pivot)."""
        from owlbear_mcp_browser.server import AppContext

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "launcher" in fields, f"'launcher' field missing from AppContext; found: {fields}"

    def test_appcontext_has_page_field(self) -> None:
        """AppContext dataclass must have a 'page' field."""
        from owlbear_mcp_browser.server import AppContext

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "page" in fields, f"'page' field missing from AppContext; found: {fields}"

    def test_appcontext_constructed_with_cdp_none(self) -> None:
        """AppContext can be constructed with launcher=None (graceful-degrade case)."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), launcher=None, page=None)
        assert ctx.launcher is None

    def test_appcontext_constructed_with_page_none(self) -> None:
        """AppContext can be constructed with page=None (graceful-degrade case)."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), launcher=None, page=None)
        assert ctx.page is None


# ===========================================================================
# TestFromAC_LifespanCDPConnect — AC2: lifespan attempts CDP; degrades on failure
# ===========================================================================


class TestFromAC_LifespanCDPConnect:
    """app_lifespan opens a Playwright session and yields AppContext with launcher+page (updated for #871)."""

    @pytest.mark.asyncio
    async def test_lifespan_successful_cdp_yields_cdp_not_none(self) -> None:
        """Successful PlaywrightLauncher start: AppContext.launcher is not None."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.launcher is not None, "ctx.launcher must not be None after successful launch"

    @pytest.mark.asyncio
    async def test_lifespan_successful_cdp_yields_page_not_none(self) -> None:
        """Successful PlaywrightLauncher start: AppContext.page is not None."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.page is not None, "ctx.page must not be None after successful launch"

    @pytest.mark.asyncio
    async def test_lifespan_failed_cdp_yields_cdp_none(self) -> None:
        """PlaywrightLauncher startup failure: AppContext.launcher is None (graceful degrade)."""
        from owlbear_mcp_browser.server import app_lifespan

        failing_launcher = MagicMock()
        failing_launcher.launch = AsyncMock(side_effect=RuntimeError("playwright unavailable"))
        failing_launcher.close = AsyncMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=failing_launcher):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.launcher is None, "ctx.launcher must be None when launch fails"

    @pytest.mark.asyncio
    async def test_lifespan_failed_cdp_yields_page_none(self) -> None:
        """PlaywrightLauncher startup failure: AppContext.page is None (graceful degrade)."""
        from owlbear_mcp_browser.server import app_lifespan

        failing_launcher = MagicMock()
        failing_launcher.launch = AsyncMock(side_effect=RuntimeError("playwright unavailable"))
        failing_launcher.close = AsyncMock()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=failing_launcher):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.page is None, "ctx.page must be None when launch fails"


# ===========================================================================
# TestFromAC_LifespanCleanup — AC3: lifespan cleanup disconnects CDP
# ===========================================================================


class TestFromAC_LifespanCleanup:
    """app_lifespan cleanup closes launcher on both clean and exception exits (updated for #871)."""

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_calls_browser_close_on_clean_exit(self) -> None:
        """PlaywrightLauncher.close() is called when the lifespan exits normally."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            server = MagicMock()
            async with app_lifespan(server):
                pass

        mock_launcher.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_calls_browser_close_on_exception_exit(self) -> None:
        """PlaywrightLauncher.close() is called even when the lifespan body raises."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            server = MagicMock()
            err_msg = "test_exception"
            with pytest.raises(RuntimeError, match=err_msg):
                async with app_lifespan(server):
                    raise RuntimeError(err_msg)

        mock_launcher.close.assert_called_once()


# ===========================================================================
# TestFromAC_NavigateTool — AC4: navigate() calls page.goto() after allowlist check
# ===========================================================================


class TestFromAC_NavigateTool:
    """navigate() must check the allowlist then delegate to page.goto(url) (AC4)."""

    @pytest.mark.asyncio
    async def test_navigate_calls_page_goto_with_url(self) -> None:
        """navigate() calls page.goto(url) when URL is in the allowlist."""
        from owlbear_mcp_browser.server import navigate

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page, allowed_domains=["example.com"])

        await navigate(ctx, "https://example.com/")

        mock_page.goto.assert_awaited_once_with("https://example.com/")

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_for_blocked_domain(self) -> None:
        """navigate() raises ToolError when URL hostname is not in the allowlist."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page, allowed_domains=[])  # deny-all allowlist

        with pytest.raises(ToolError):
            await navigate(ctx, "https://notallowed.example/")

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_when_page_is_none(self) -> None:
        """navigate() raises ToolError when AppContext.page is None (no active session)."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        ctx = _make_ctx_with_page(None, allowed_domains=["example.com"])

        with pytest.raises(ToolError):
            await navigate(ctx, "https://example.com/")


# ===========================================================================
# TestFromAC_ClickTool — AC5: click() calls page.locator(selector).click()
# ===========================================================================


class TestFromAC_ClickTool:
    """click() must use page.locator(selector).click() (AC5)."""

    @pytest.mark.asyncio
    async def test_click_calls_page_locator_click(self) -> None:
        """click() calls page.locator(selector).click()."""
        from owlbear_mcp_browser.server import click

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page)

        await click(ctx, "#submit-btn")

        mock_page.locator.assert_called_once_with("#submit-btn")
        mock_page.locator.return_value.click.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_click_raises_tool_error_when_page_is_none(self) -> None:
        """click() raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import click

        ctx = _make_ctx_with_page(None)

        with pytest.raises(ToolError):
            await click(ctx, "#btn")


# ===========================================================================
# TestFromAC_TypeTool — AC6: type_input() calls page.locator(selector).fill(text)
# ===========================================================================


class TestFromAC_TypeTool:
    """type_input() must use page.locator(selector).fill(text) (AC6)."""

    @pytest.mark.asyncio
    async def test_type_input_calls_page_locator_fill(self) -> None:
        """type_input() calls page.locator(selector).fill(text)."""
        from owlbear_mcp_browser.server import type_input

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page)

        await type_input(ctx, "#search", "hello world")

        mock_page.locator.assert_called_once_with("#search")
        mock_page.locator.return_value.fill.assert_awaited_once_with("hello world")

    @pytest.mark.asyncio
    async def test_type_input_raises_tool_error_when_page_is_none(self) -> None:
        """type_input() raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import type_input

        ctx = _make_ctx_with_page(None)

        with pytest.raises(ToolError):
            await type_input(ctx, "#field", "text")


# ===========================================================================
# TestFromAC_SelectTool — AC7: select() calls page.locator(selector).select_option(value)
# ===========================================================================


class TestFromAC_SelectTool:
    """select() must use page.locator(selector).select_option(value) (AC7)."""

    @pytest.mark.asyncio
    async def test_select_calls_page_locator_select_option(self) -> None:
        """select() calls page.locator(selector).select_option(value)."""
        from owlbear_mcp_browser.server import select

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page)

        await select(ctx, "#dropdown", "option-b")

        mock_page.locator.assert_called_once_with("#dropdown")
        mock_page.locator.return_value.select_option.assert_awaited_once_with("option-b")

    @pytest.mark.asyncio
    async def test_select_raises_tool_error_when_page_is_none(self) -> None:
        """select() raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import select

        ctx = _make_ctx_with_page(None)

        with pytest.raises(ToolError):
            await select(ctx, "#list", "val")


# ===========================================================================
# TestFromAC_ReadTextTool — AC8: read_text() calls extract_content(html, url)
# ===========================================================================


class TestFromAC_ReadTextTool:
    """read_text() must call extract_content(page.content(), page.url) (AC8)."""

    @pytest.mark.asyncio
    async def test_read_text_calls_extract_content_with_page_html_and_url(self) -> None:
        """read_text() calls page.content() and extract_content(html, url), returns result."""
        from owlbear_mcp_browser.server import read_text

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page)

        # Patch extract_content where server.py will import it from
        with patch(
            "owlbear_mcp_browser.server.extract_content",
            return_value="# Hello",
        ) as mock_extract:
            result = await read_text(ctx)

        mock_page.content.assert_awaited_once()
        mock_extract.assert_called_once_with(
            "<html><body><h1>Hello</h1></body></html>",
            mock_page.url,
        )
        assert result == "# Hello"

    @pytest.mark.asyncio
    async def test_read_text_returns_string_when_page_is_none(self) -> None:
        """read_text() returns last_content fallback (empty string) when page is None.

        Adjudicated in #877: read_text has a fetcher-only pipeline fallback. A browser
        page is not required — return last_content (may be "") instead of raising ToolError.
        """
        from owlbear_mcp_browser.server import read_text

        ctx = _make_ctx_with_page(None)

        # FAILS on HEAD: read_text still raises ToolError instead of returning last_content
        result = await read_text(ctx)
        assert isinstance(result, str)


# ===========================================================================
# TestFromAC_SnapshotTool — AC9: snapshot() calls page.aria_snapshot() as markdown
# ===========================================================================


class TestFromAC_SnapshotTool:
    """snapshot() must call page.aria_snapshot() and return its output (AC9)."""

    @pytest.mark.asyncio
    async def test_snapshot_calls_page_aria_snapshot_and_returns_result(self) -> None:
        """snapshot() calls page.aria_snapshot() and returns the markdown string."""
        from owlbear_mcp_browser.server import snapshot

        mock_page = _make_mock_page()
        ctx = _make_ctx_with_page(mock_page)

        result = await snapshot(ctx)

        mock_page.locator("body").aria_snapshot.assert_awaited_once()
        assert result == "- heading 'Hello' [level=1]"

    @pytest.mark.asyncio
    async def test_snapshot_returns_string_when_page_is_none(self) -> None:
        """snapshot() returns last_content fallback (empty string) when page is None.

        Adjudicated in #877: snapshot has a fetcher-only pipeline fallback. A browser
        page is not required — return last_content (may be "") instead of raising ToolError.
        """
        from owlbear_mcp_browser.server import snapshot

        ctx = _make_ctx_with_page(None)

        # FAILS on HEAD: snapshot still raises ToolError instead of returning last_content
        result = await snapshot(ctx)
        assert isinstance(result, str)
