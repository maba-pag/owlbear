"""Tests for BrowserManager — async context manager lifecycle.

Covers: launch/close via async context manager, browser reuse within
context, cleanup on exception, respects BrowserConfig headless and
viewport options.  All Playwright calls are mocked (no real browser).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.tools.browser.config import BrowserConfig

# ---------------------------------------------------------------------------
# Shared mock fixture
# ---------------------------------------------------------------------------

MODULE = "owlbear.tools.browser.manager"


@pytest.fixture
def pw_mocks():
    """Build a complete Playwright mock chain.

    Returns a dict with keys: page, context, browser, pw, pw_instance.
    ``pw_instance.start()`` → ``pw`` (Playwright object)
    ``pw.chromium.launch()`` → ``browser``
    ``browser.new_context()`` → ``context``
    ``context.new_page()`` → ``page``
    """
    mock_page = AsyncMock(name="Page")
    # set_default_timeout is synchronous in Playwright — use MagicMock
    mock_page.set_default_timeout = MagicMock()
    mock_context = AsyncMock(name="BrowserContext")
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser = AsyncMock(name="Browser")
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_pw = AsyncMock(name="Playwright")
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    # async_playwright() returns an object whose .start() yields the pw
    mock_pw_instance = AsyncMock(name="PlaywrightContextManager")
    mock_pw_instance.start = AsyncMock(return_value=mock_pw)

    # CDP-mode mocks — connect_over_cdp returns a browser with pre-populated contexts
    mock_cdp_page = AsyncMock(name="CDPPage")
    mock_cdp_page.set_default_timeout = MagicMock()
    mock_cdp_context = AsyncMock(name="CDPBrowserContext")
    mock_cdp_context.new_page = AsyncMock(return_value=mock_cdp_page)
    mock_cdp_browser = AsyncMock(name="CDPBrowser")
    mock_cdp_browser.contexts = [mock_cdp_context]
    mock_cdp_browser.new_context = AsyncMock()
    mock_pw.chromium.connect_over_cdp = AsyncMock(return_value=mock_cdp_browser)

    return {
        "page": mock_page,
        "context": mock_context,
        "browser": mock_browser,
        "pw": mock_pw,
        "pw_instance": mock_pw_instance,
        "cdp_page": mock_cdp_page,
        "cdp_context": mock_cdp_context,
        "cdp_browser": mock_cdp_browser,
    }


# ---------------------------------------------------------------------------
# Context manager basics
# ---------------------------------------------------------------------------


class TestBrowserManagerContextManager:
    """Entering the context manager sets up Playwright and returns self."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_enter_returns_self(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            mgr = BrowserManager()
            result = await mgr.__aenter__()
            assert result is mgr
            await mgr.__aexit__(None, None, None)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_async_with_syntax(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                assert mgr is not None


# ---------------------------------------------------------------------------
# Page property
# ---------------------------------------------------------------------------


class TestBrowserManagerPage:
    """The ``page`` property exposes the current Playwright page."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_page_property_returns_active_page(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                assert mgr.page is pw_mocks["page"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_page_is_same_object_throughout_context(self, pw_mocks):
        """Browser and page are reused — no re-creation within the context."""
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                page1 = mgr.page
                page2 = mgr.page
                assert page1 is page2


# ---------------------------------------------------------------------------
# Launch configuration
# ---------------------------------------------------------------------------


class TestBrowserManagerLaunchConfig:
    """BrowserManager respects BrowserConfig options."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launches_chromium_headless_false_by_default(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager():
                pw_mocks["pw"].chromium.launch.assert_awaited_once_with(headless=False)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launches_chromium_headless_true(self, pw_mocks):
        cfg = BrowserConfig(headless=True)
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["pw"].chromium.launch.assert_awaited_once_with(headless=True)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_creates_context_with_default_viewport(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager():
                pw_mocks["browser"].new_context.assert_awaited_once_with(
                    viewport={"width": 1280, "height": 720},
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_creates_context_with_custom_viewport(self, pw_mocks):
        cfg = BrowserConfig(viewport=(1920, 1080))
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["browser"].new_context.assert_awaited_once_with(
                    viewport={"width": 1920, "height": 1080},
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sets_default_timeout(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager():
                pw_mocks["page"].set_default_timeout.assert_called_once_with(30_000)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sets_custom_timeout(self, pw_mocks):
        cfg = BrowserConfig(timeout_ms=60_000)
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["page"].set_default_timeout.assert_called_once_with(60_000)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestBrowserManagerCleanup:
    """All resources are closed in reverse order on exit."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cleanup_on_normal_exit(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager():
                pass

            pw_mocks["page"].close.assert_awaited_once()
            pw_mocks["context"].close.assert_awaited_once()
            pw_mocks["browser"].close.assert_awaited_once()
            pw_mocks["pw"].stop.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cleanup_on_exception(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            msg = "boom"
            with pytest.raises(RuntimeError, match="boom"):
                async with BrowserManager():
                    raise RuntimeError(msg)

            # All resources must still be closed despite the exception
            pw_mocks["page"].close.assert_awaited_once()
            pw_mocks["context"].close.assert_awaited_once()
            pw_mocks["browser"].close.assert_awaited_once()
            pw_mocks["pw"].stop.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cleanup_order(self, pw_mocks):
        """Resources close in reverse order: page → context → browser → pw."""
        call_order: list[str] = []

        def track(name: str):
            call_order.append(name)

        pw_mocks["page"].close = AsyncMock(side_effect=lambda: track("page"))
        pw_mocks["context"].close = AsyncMock(side_effect=lambda: track("context"))
        pw_mocks["browser"].close = AsyncMock(side_effect=lambda: track("browser"))
        pw_mocks["pw"].stop = AsyncMock(side_effect=lambda: track("pw"))

        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager():
                pass

        assert call_order == ["page", "context", "browser", "pw"]


# ---------------------------------------------------------------------------
# CDP connect mode
# ---------------------------------------------------------------------------


class TestBrowserManagerCDPConnect:
    """CDP connect mode: connect to existing browser via DevTools Protocol."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_calls_connect_over_cdp(self, pw_mocks):
        """When cdp_endpoint is set, __aenter__ calls connect_over_cdp."""
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["pw"].chromium.connect_over_cdp.assert_awaited_once_with(
                    "http://localhost:9222",
                )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_does_not_call_launch(self, pw_mocks):
        """CDP mode must not call launch."""
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["pw"].chromium.launch.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_reuses_existing_context(self, pw_mocks):
        """Reuses browser.contexts[0], does not call new_context."""
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg) as mgr:
                assert mgr._context is pw_mocks["cdp_context"]
                pw_mocks["cdp_browser"].new_context.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_opens_new_page_in_reused_context(self, pw_mocks):
        """Opens new page via context.new_page() on the reused context."""
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg) as mgr:
                pw_mocks["cdp_context"].new_page.assert_awaited_once()
                assert mgr.page is pw_mocks["cdp_page"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_sets_page_timeout(self, pw_mocks):
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222", timeout_ms=45_000)
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pw_mocks["cdp_page"].set_default_timeout.assert_called_once_with(45_000)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_sets_is_cdp_flag(self, pw_mocks):
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg) as mgr:
                assert mgr._is_cdp is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_launch_sets_is_cdp_false(self, pw_mocks):
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager() as mgr:
                assert mgr._is_cdp is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_tracks_owned_pages(self, pw_mocks):
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg) as mgr:
                assert pw_mocks["cdp_page"] in mgr._owned_pages


# ---------------------------------------------------------------------------
# CDP cleanup
# ---------------------------------------------------------------------------


class TestBrowserManagerCDPCleanup:
    """CDP cleanup: close owned pages + disconnect (never close browser)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_closes_owned_pages(self, pw_mocks):
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

            pw_mocks["cdp_page"].close.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_disconnects_not_closes(self, pw_mocks):
        """CDP mode calls disconnect() — never close() on the browser."""
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

            pw_mocks["cdp_browser"].disconnect.assert_awaited_once()
            pw_mocks["cdp_browser"].close.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_does_not_close_context(self, pw_mocks):
        """CDP mode never closes the reused context (owned by the user)."""
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

            pw_mocks["cdp_context"].close.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_stops_playwright(self, pw_mocks):
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

            pw_mocks["pw"].stop.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_cleanup_on_exception(self, pw_mocks):
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            msg = "boom"
            with pytest.raises(RuntimeError, match="boom"):
                async with BrowserManager(config=cfg):
                    raise RuntimeError(msg)

            pw_mocks["cdp_page"].close.assert_awaited_once()
            pw_mocks["cdp_browser"].disconnect.assert_awaited_once()
            pw_mocks["cdp_browser"].close.assert_not_awaited()
            pw_mocks["pw"].stop.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_cleanup_order(self, pw_mocks):
        """CDP resources close in order: owned pages → disconnect → pw.stop."""
        call_order: list[str] = []

        def track(name: str):
            call_order.append(name)

        pw_mocks["cdp_page"].close = AsyncMock(side_effect=lambda: track("page"))
        pw_mocks["cdp_browser"].disconnect = AsyncMock(
            side_effect=lambda: track("disconnect"),
        )
        pw_mocks["pw"].stop = AsyncMock(side_effect=lambda: track("pw"))

        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager(config=cfg):
                pass

        assert call_order == ["page", "disconnect", "pw"]


# ---------------------------------------------------------------------------
# CDP error handling
# ---------------------------------------------------------------------------


class TestBrowserManagerCDPErrors:
    """Error cases for CDP connect mode."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_unreachable_raises_connection_error(self, pw_mocks):
        """When CDP endpoint is unreachable, raises ConnectionError."""
        pw_mocks["pw"].chromium.connect_over_cdp = AsyncMock(
            side_effect=Exception("Connection refused"),
        )
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            with pytest.raises(ConnectionError):
                async with BrowserManager(config=cfg):
                    pass

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cdp_unreachable_stops_playwright(self, pw_mocks):
        """Playwright is stopped even when CDP connection fails."""
        pw_mocks["pw"].chromium.connect_over_cdp = AsyncMock(
            side_effect=Exception("Connection refused"),
        )
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            with pytest.raises(ConnectionError):
                async with BrowserManager(config=cfg):
                    pass

            pw_mocks["pw"].stop.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_cdp_uses_launch_mode(self, pw_mocks):
        """When cdp_endpoint is None, launch mode is used (not CDP)."""
        with patch(f"{MODULE}.async_playwright", return_value=pw_mocks["pw_instance"]):
            from owlbear.tools.browser.manager import BrowserManager

            async with BrowserManager():
                pw_mocks["pw"].chromium.launch.assert_awaited_once()
                pw_mocks["pw"].chromium.connect_over_cdp.assert_not_awaited()
