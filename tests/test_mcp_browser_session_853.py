"""Failing RED-phase tests for #853: mcp-browser session management.

AC coverage:
  AC1  AppContext includes CDPConnectionManager and optional Page fields
  AC2  lifespan: successful CDP connection yields AppContext with cdp+page
  AC3  lifespan: failed CDP connection yields AppContext with cdp=None, page=None
  AC4  lifespan cleanup: disconnects CDP and closes page on exit
  AC5  navigate(): checks allowlist then calls page.goto(url)
  AC6  click(): calls page.locator(selector).click()
  AC7  type(): calls page.locator(selector).fill(text)
  AC8  select(): calls page.locator(selector).select_option(value)
  AC9  read_text(): calls extract_content(page.content(), page.url)
  AC10 snapshot(): calls page.aria_snapshot()
  AC11 all tools: raise ToolError when page is None

All tests FAIL on current HEAD:
  - AC1: AppContext has no cdp/page fields → AttributeError/TypeError
  - AC2-AC4: CDPConnectionManager not imported in server.py → AttributeError on patch
  - AC5-AC10: helper _make_mcp_ctx_with_page raises TypeError (AppContext lacks cdp/page);
              tool signatures lack ctx param → TypeError
  - AC11: _make_mcp_ctx_no_page raises TypeError; tools don't check page → ToolError not raised
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
    page.aria_snapshot = AsyncMock(return_value="# Snapshot\n- item 1")
    page.locator = MagicMock(return_value=_make_mock_locator())
    return page


def _make_mock_cdp(page: MagicMock) -> MagicMock:
    """Return a mock CDPConnectionManager wired with one Playwright context/page."""
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.contexts = [context]
    cdp = MagicMock()
    cdp._browser = browser
    cdp.connect = AsyncMock()
    cdp.disconnect = AsyncMock()
    return cdp


def _make_mcp_ctx_with_page(page: MagicMock) -> MagicMock:
    """Return a mock MCP ctx whose lifespan_context has cdp and page set."""
    from owlbear_mcp_browser.allowlist import DomainAllowlist
    from owlbear_mcp_browser.server import AppContext

    app_ctx = AppContext(
        allowlist=DomainAllowlist(domains=["sharepoint.example.com"]),
        cdp=MagicMock(),
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
        cdp=None,
        page=None,
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_AppContextFields — AC1
# ===========================================================================


class TestFromAC_AppContextFields:
    """AC1: AppContext dataclass must expose cdp and page as optional fields."""

    def test_appcontext_cdp_defaults_to_none(self) -> None:
        """AppContext constructed with only allowlist must have cdp=None by default."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert ctx.cdp is None  # FAILS: no cdp field on current HEAD

    def test_appcontext_page_defaults_to_none(self) -> None:
        """AppContext constructed with only allowlist must have page=None by default."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert ctx.page is None  # FAILS: no page field on current HEAD

    def test_appcontext_accepts_cdp_kwarg(self) -> None:
        """AppContext constructor must accept cdp keyword argument and store it."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        mock_cdp = MagicMock()
        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), cdp=mock_cdp)
        assert ctx.cdp is mock_cdp  # FAILS: TypeError on current HEAD (unexpected kwarg)

    def test_appcontext_accepts_page_kwarg(self) -> None:
        """AppContext constructor must accept page keyword argument and store it."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        mock_page = MagicMock()
        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        assert ctx.page is mock_page  # FAILS: TypeError on current HEAD (unexpected kwarg)


# ===========================================================================
# TestFromAC_LifespanSuccessfulConnection — AC2
# ===========================================================================


class TestFromAC_LifespanSuccessfulConnection:
    """AC2: Successful CDP connect yields AppContext with cdp and page populated."""

    @pytest.mark.asyncio
    async def test_lifespan_sets_cdp_on_successful_connect(self) -> None:
        """App lifespan sets ctx.cdp to the CDPConnectionManager instance when connect succeeds."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.cdp is mock_cdp

    @pytest.mark.asyncio
    async def test_lifespan_sets_page_on_successful_connect(self) -> None:
        """App lifespan sets ctx.page from cdp._browser.contexts[0].new_page() when CDP connects."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.page is mock_page

    @pytest.mark.asyncio
    async def test_lifespan_calls_cdp_connect(self) -> None:
        """App lifespan calls CDPConnectionManager.connect() during startup."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as _:
                pass

        mock_cdp.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_calls_new_page(self) -> None:
        """App lifespan calls cdp._browser.contexts[0].new_page() to open the shared page."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as _:
                pass

        mock_cdp._browser.contexts[0].new_page.assert_called_once()


# ===========================================================================
# TestFromAC_LifespanFailedConnection — AC3
# ===========================================================================


class TestFromAC_LifespanFailedConnection:
    """AC3: When CDPConnectionManager.connect() raises, lifespan yields cdp=None, page=None."""

    @pytest.mark.asyncio
    async def test_lifespan_sets_cdp_none_on_failed_connect(self) -> None:
        """ctx.cdp is None when CDP connect raises (no Edge running)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_cdp = MagicMock()
        mock_cdp.connect = AsyncMock(side_effect=ConnectionRefusedError("no Edge"))
        mock_cdp.disconnect = AsyncMock()
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.cdp is None

    @pytest.mark.asyncio
    async def test_lifespan_sets_page_none_on_failed_connect(self) -> None:
        """ctx.page is None when CDP connect raises (no Edge running)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_cdp = MagicMock()
        mock_cdp.connect = AsyncMock(side_effect=ConnectionRefusedError("no Edge"))
        mock_cdp.disconnect = AsyncMock()
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.page is None


# ===========================================================================
# TestFromAC_LifespanCleanup — AC4
# ===========================================================================


class TestFromAC_LifespanCleanup:
    """AC4: Lifespan finally-block closes page and disconnects CDP on exit."""

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_closes_page(self) -> None:
        """App lifespan calls page.close() after yielding (cleanup on session end)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as _:
                pass

        mock_page.close.assert_called_once()  # FAILS: no cleanup in current lifespan

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_disconnects_cdp(self) -> None:
        """App lifespan calls cdp.disconnect() after yielding (cleanup on session end)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as _:
                pass

        mock_cdp.disconnect.assert_called_once()  # FAILS: no cleanup in current lifespan

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_skipped_when_connect_failed(self) -> None:
        """When CDP connect failed (cdp=None), lifespan exits without calling disconnect."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_cdp = MagicMock()
        mock_cdp.connect = AsyncMock(side_effect=Exception("no browser"))
        mock_cdp.disconnect = AsyncMock()
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(mock_server) as _:
                pass

        mock_cdp.disconnect.assert_not_called()


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

        mock_page.aria_snapshot.assert_called_once()
        assert result == "# Snapshot\n- item 1"


# ===========================================================================
# TestFromAC_ToolErrorWhenNoPage — AC11
# ===========================================================================


class TestFromAC_ToolErrorWhenNoPage:
    """AC11: Every tool raises ToolError when ctx.lifespan_context.page is None."""

    @pytest.mark.asyncio
    async def test_navigate_raises_when_page_none(self) -> None:
        """navigate raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await navigate(ctx, _ALLOWED_URL)  # FAILS: navigate has no ctx param + no page check

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
    async def test_read_text_raises_when_page_none(self) -> None:
        """read_text raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import read_text

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await read_text(ctx)  # FAILS: read_text has no ctx param + no page check

    @pytest.mark.asyncio
    async def test_snapshot_raises_when_page_none(self) -> None:
        """snapshot raises ToolError when AppContext.page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import snapshot

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError):
            await snapshot(ctx)  # FAILS: snapshot has no ctx param + no page check
