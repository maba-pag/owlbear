"""Failing RED-phase tests for #854: mcp-browser session management (GREEN).

AC coverage — gaps beyond #853's 27 tests:
  AC2b  Lifespan reads BROWSER_CDP_PORT env; default port 9222 when absent
  AC4b  Lifespan finally-block closes page and disconnects CDP even on exception
  AC11b All tools raise ToolError with message "No browser session" when page is None

All tests FAIL on current HEAD:
  - AC2b: CDPConnectionManager not imported in server.py → AttributeError on patch
  - AC4b: No CDP integration in current lifespan → cleanup assertions fail under exception
  - AC11b: navigate() raises wrong message; click/type/select/snapshot raise no ToolError;
           read_text() raises no ToolError → pytest.raises(ToolError, match=...) fails
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_URL = "https://sharepoint.example.com/sites/team"
_BLOCKED_URL = "https://evil.example.net/malware"
_SELECTOR = "#submit-btn"
_TEXT_INPUT = "hello"
_OPTION_VALUE = "opt-b"
_NO_SESSION_MSG = "No browser session"
_CUSTOM_PORT = 9333


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_locator() -> MagicMock:
    loc = MagicMock()
    loc.click = AsyncMock()
    loc.fill = AsyncMock()
    loc.select_option = AsyncMock()
    return loc


def _make_mock_page() -> MagicMock:
    page = MagicMock()
    page.url = _ALLOWED_URL
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html/>")
    page.close = AsyncMock()
    loc = _make_mock_locator()
    loc.aria_snapshot = AsyncMock(return_value="# snap")
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


def _make_mcp_ctx_no_page() -> MagicMock:
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
# TestFromAC_LifespanCDPPort — AC2 (gap: env var and default port)
# ===========================================================================


class TestFromAC_LifespanCDPPort:
    """AC2: Lifespan uses PlaywrightLauncher (updated for #871: CDP port removed)."""

    @pytest.mark.asyncio
    async def test_lifespan_uses_default_port_9222_when_env_not_set(self) -> None:
        """PlaywrightLauncher is instantiated when lifespan runs (CDP port no longer used)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        env = {k: v for k, v in os.environ.items() if k != "BROWSER_CDP_PORT"}
        with patch.dict(os.environ, env, clear=True), patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher) as mock_launcher_cls:
            async with app_lifespan(mock_server) as _:
                pass

        mock_launcher_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_uses_browser_cdp_port_env_when_set(self) -> None:
        """BROWSER_CDP_PORT env var does not affect PlaywrightLauncher (pivot removed CDP port)."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch.dict(os.environ, {"BROWSER_CDP_PORT": str(_CUSTOM_PORT)}), patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher) as mock_launcher_cls:
            async with app_lifespan(mock_server) as _:
                pass

        # BROWSER_CDP_PORT is ignored; PlaywrightLauncher is still used
        mock_launcher_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_converts_cdp_port_env_string_to_int(self) -> None:
        """Lifespan does not use BROWSER_CDP_PORT at all after Playwright pivot."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()

        with patch.dict(os.environ, {"BROWSER_CDP_PORT": "99999"}), patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher) as mock_launcher_cls:
            async with app_lifespan(mock_server) as ctx:
                # Lifespan must succeed despite invalid port (port is ignored)
                assert ctx.launcher is not None

        mock_launcher_cls.assert_called_once()


# ===========================================================================
# TestFromAC_LifespanCleanupOnException — AC4 (gap: finally on exception)
# ===========================================================================


class TestFromAC_LifespanCleanupOnException:
    """AC4: Lifespan finally-block must run cleanup even when an exception propagates."""

    @pytest.mark.asyncio
    async def test_lifespan_closes_page_on_exception_during_body(self) -> None:
        """page.close() is called in finally even when the lifespan body raises."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()
        err_msg = "simulated server error"

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher), pytest.raises(RuntimeError):
            async with app_lifespan(mock_server) as _:
                raise RuntimeError(err_msg)

        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_disconnects_cdp_on_exception_during_body(self) -> None:
        """launcher.close() is called in finally even when the lifespan body raises."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_server = MagicMock()
        err_msg = "simulated server error"

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher), pytest.raises(RuntimeError):
            async with app_lifespan(mock_server) as _:
                raise RuntimeError(err_msg)

        mock_launcher.close.assert_called_once()


# ===========================================================================
# TestFromAC_NoSessionMessage — AC11 (gap: error message must be "No browser session")
# ===========================================================================


class TestFromAC_NoSessionMessage:
    """AC11: All tools must raise ToolError('No browser session') when page is None."""

    @pytest.mark.asyncio
    async def test_navigate_no_session_message(self) -> None:
        """navigate raises ToolError with message 'No browser session' when page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError, match=_NO_SESSION_MSG):
            await navigate(ctx, _ALLOWED_URL)  # FAILS: wrong message on current HEAD

    @pytest.mark.asyncio
    async def test_click_no_session_message(self) -> None:
        """click raises ToolError with message 'No browser session' when page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import click

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError, match=_NO_SESSION_MSG):
            await click(ctx, _SELECTOR)  # FAILS: click has no ctx param + raises no ToolError

    @pytest.mark.asyncio
    async def test_type_no_session_message(self) -> None:
        """type_input raises ToolError with message 'No browser session' when page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import type_input

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError, match=_NO_SESSION_MSG):
            await type_input(ctx, _SELECTOR, _TEXT_INPUT)  # FAILS: no ctx param + no ToolError

    @pytest.mark.asyncio
    async def test_select_no_session_message(self) -> None:
        """select raises ToolError with message 'No browser session' when page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import select

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError, match=_NO_SESSION_MSG):
            await select(ctx, _SELECTOR, _OPTION_VALUE)  # FAILS: no ctx param + no ToolError

    @pytest.mark.asyncio
    async def test_read_text_no_session_message(self) -> None:
        """read_text raises ToolError with message 'No browser session' when page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import read_text

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError, match=_NO_SESSION_MSG):
            await read_text(ctx)  # FAILS: returns last_content instead of raising ToolError

    @pytest.mark.asyncio
    async def test_snapshot_no_session_message(self) -> None:
        """snapshot raises ToolError with message 'No browser session' when page is None."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import snapshot

        ctx = _make_mcp_ctx_no_page()  # FAILS: AppContext lacks cdp/page

        with pytest.raises(ToolError, match=_NO_SESSION_MSG):
            await snapshot(ctx)  # FAILS: snapshot has no ctx param + raises no ToolError
