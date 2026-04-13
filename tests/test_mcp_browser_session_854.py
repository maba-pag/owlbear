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
    page.aria_snapshot = AsyncMock(return_value="# snap")
    page.locator = MagicMock(return_value=_make_mock_locator())
    return page


def _make_mock_cdp(page: MagicMock) -> MagicMock:
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.contexts = [context]
    cdp = MagicMock()
    cdp._browser = browser
    cdp.connect = AsyncMock()
    cdp.disconnect = AsyncMock()
    return cdp


def _make_mcp_ctx_no_page() -> MagicMock:
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
# TestFromAC_LifespanCDPPort — AC2 (gap: env var and default port)
# ===========================================================================


class TestFromAC_LifespanCDPPort:
    """AC2: Lifespan reads BROWSER_CDP_PORT and defaults to 9222 when absent."""

    @pytest.mark.asyncio
    async def test_lifespan_uses_default_port_9222_when_env_not_set(self) -> None:
        """CDPConnectionManager is instantiated with port=9222 when BROWSER_CDP_PORT is unset."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        env = {k: v for k, v in os.environ.items() if k != "BROWSER_CDP_PORT"}
        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch.dict(os.environ, env, clear=True), patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp) as mock_cdp_cls:
            async with app_lifespan(mock_server) as _:
                pass

        mock_cdp_cls.assert_called_once_with(port=9222)

    @pytest.mark.asyncio
    async def test_lifespan_uses_browser_cdp_port_env_when_set(self) -> None:
        """CDPConnectionManager is instantiated with port from BROWSER_CDP_PORT env var."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch.dict(os.environ, {"BROWSER_CDP_PORT": str(_CUSTOM_PORT)}), patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp) as mock_cdp_cls:
            async with app_lifespan(mock_server) as _:
                pass

        mock_cdp_cls.assert_called_once_with(port=_CUSTOM_PORT)

    @pytest.mark.asyncio
    async def test_lifespan_converts_cdp_port_env_string_to_int(self) -> None:
        """BROWSER_CDP_PORT is an env string; it must be coerced to int for CDPConnectionManager."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch.dict(os.environ, {"BROWSER_CDP_PORT": "9444"}), patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp) as mock_cdp_cls:
            async with app_lifespan(mock_server) as _:
                pass

        call_port = mock_cdp_cls.call_args.kwargs.get("port") or mock_cdp_cls.call_args.args[0]
        assert isinstance(call_port, int), f"port must be int, got {type(call_port)}"
        assert call_port == 9444


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
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()
        err_msg = "simulated server error"

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp), pytest.raises(RuntimeError):
            async with app_lifespan(mock_server) as _:
                raise RuntimeError(err_msg)

        mock_page.close.assert_called_once()  # FAILS: no cdp wiring or finally cleanup

    @pytest.mark.asyncio
    async def test_lifespan_disconnects_cdp_on_exception_during_body(self) -> None:
        """cdp.disconnect() is called in finally even when the lifespan body raises."""
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_cdp = _make_mock_cdp(mock_page)
        mock_server = MagicMock()
        err_msg = "simulated server error"

        # FAILS: CDPConnectionManager not imported in server.py → AttributeError on patch
        with patch("owlbear_mcp_browser.server.CDPConnectionManager", return_value=mock_cdp), pytest.raises(RuntimeError):
            async with app_lifespan(mock_server) as _:
                raise RuntimeError(err_msg)

        mock_cdp.disconnect.assert_called_once()  # FAILS: no cdp wiring or finally cleanup


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
