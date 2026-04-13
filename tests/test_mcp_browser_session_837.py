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
    page.content = AsyncMock(return_value="<html><body><h1>Hello</h1></body></html>")
    page.aria_snapshot = AsyncMock(return_value="- heading 'Hello' [level=1]")
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.select_option = AsyncMock()
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


def _make_ctx_with_page(
    page: MagicMock | None,
    *,
    cdp: MagicMock | None = None,
    allowed_domains: list[str] | None = None,
) -> MagicMock:
    """Return a mock MCP Context whose lifespan_context exposes page, cdp, and allowlist.

    Uses SimpleNamespace so the test does not depend on AppContext having new fields yet —
    the tool implementation is what is under test, not the dataclass construction.
    """
    from owlbear_mcp_browser.allowlist import DomainAllowlist

    domains: list[str] = allowed_domains if allowed_domains is not None else ["example.com"]
    lc = SimpleNamespace(
        allowlist=DomainAllowlist(domains=domains),
        cdp=cdp,
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
        """AppContext dataclass must have a 'cdp' field."""
        from owlbear_mcp_browser.server import AppContext

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "cdp" in fields, f"'cdp' field missing from AppContext; found: {fields}"

    def test_appcontext_has_page_field(self) -> None:
        """AppContext dataclass must have a 'page' field."""
        from owlbear_mcp_browser.server import AppContext

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "page" in fields, f"'page' field missing from AppContext; found: {fields}"

    def test_appcontext_constructed_with_cdp_none(self) -> None:
        """AppContext can be constructed with cdp=None (graceful-degrade case)."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), cdp=None, page=None)
        assert ctx.cdp is None

    def test_appcontext_constructed_with_page_none(self) -> None:
        """AppContext can be constructed with page=None (graceful-degrade case)."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), cdp=None, page=None)
        assert ctx.page is None


# ===========================================================================
# TestFromAC_LifespanCDPConnect — AC2: lifespan attempts CDP; degrades on failure
# ===========================================================================


class TestFromAC_LifespanCDPConnect:
    """app_lifespan opens a CDP connection and yields AppContext with cdp+page (AC2)."""

    @pytest.mark.asyncio
    async def test_lifespan_successful_cdp_yields_cdp_not_none(self) -> None:
        """Successful CDP connect: AppContext.cdp is not None after lifespan entry."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_browser = _make_mock_browser(mock_page)

        with patch(
            "owlbear_browser.cdp.playwright_connect_over_cdp",
            new=AsyncMock(return_value=mock_browser),
        ):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.cdp is not None, "ctx.cdp must not be None after successful CDP connect"

    @pytest.mark.asyncio
    async def test_lifespan_successful_cdp_yields_page_not_none(self) -> None:
        """Successful CDP connect: AppContext.page is not None after lifespan entry."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_browser = _make_mock_browser(mock_page)

        with patch(
            "owlbear_browser.cdp.playwright_connect_over_cdp",
            new=AsyncMock(return_value=mock_browser),
        ):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.page is not None, "ctx.page must not be None after successful CDP connect"

    @pytest.mark.asyncio
    async def test_lifespan_failed_cdp_yields_cdp_none(self) -> None:
        """CDPConnectionError during connect: AppContext.cdp is None (graceful degrade)."""
        from owlbear_mcp_browser.server import app_lifespan

        # TimeoutError → CDPConnectionManager.connect() raises CDPConnectionError
        with patch(
            "owlbear_browser.cdp.playwright_connect_over_cdp",
            new=AsyncMock(side_effect=TimeoutError("no browser")),
        ):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.cdp is None, "ctx.cdp must be None when CDP connection fails"

    @pytest.mark.asyncio
    async def test_lifespan_failed_cdp_yields_page_none(self) -> None:
        """CDPConnectionError during connect: AppContext.page is None (graceful degrade)."""
        from owlbear_mcp_browser.server import app_lifespan

        with patch(
            "owlbear_browser.cdp.playwright_connect_over_cdp",
            new=AsyncMock(side_effect=TimeoutError("no browser")),
        ):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert ctx.page is None, "ctx.page must be None when CDP connection fails"


# ===========================================================================
# TestFromAC_LifespanCleanup — AC3: lifespan cleanup disconnects CDP
# ===========================================================================


class TestFromAC_LifespanCleanup:
    """app_lifespan cleanup disconnects browser on both clean and exception exits (AC3)."""

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_calls_browser_close_on_clean_exit(self) -> None:
        """Browser.close() is awaited when the lifespan exits normally."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_browser = _make_mock_browser(mock_page)

        with patch(
            "owlbear_browser.cdp.playwright_connect_over_cdp",
            new=AsyncMock(return_value=mock_browser),
        ):
            server = MagicMock()
            async with app_lifespan(server):
                pass

        # CDPConnectionManager.disconnect() calls browser.close()
        mock_browser.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_calls_browser_close_on_exception_exit(self) -> None:
        """Browser.close() is awaited even when the lifespan body raises an exception."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_browser = _make_mock_browser(mock_page)

        with patch(
            "owlbear_browser.cdp.playwright_connect_over_cdp",
            new=AsyncMock(return_value=mock_browser),
        ):
            server = MagicMock()
            err_msg = "test_exception"
            with pytest.raises(RuntimeError, match=err_msg):
                async with app_lifespan(server):
                    raise RuntimeError(err_msg)

        mock_browser.close.assert_awaited_once()


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
    async def test_read_text_raises_tool_error_when_page_is_none(self) -> None:
        """read_text() raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import read_text

        ctx = _make_ctx_with_page(None)

        with pytest.raises(ToolError):
            await read_text(ctx)


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

        mock_page.aria_snapshot.assert_awaited_once()
        assert result == "- heading 'Hello' [level=1]"

    @pytest.mark.asyncio
    async def test_snapshot_raises_tool_error_when_page_is_none(self) -> None:
        """snapshot() raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import snapshot

        ctx = _make_ctx_with_page(None)

        with pytest.raises(ToolError):
            await snapshot(ctx)
