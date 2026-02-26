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
    return {
        "page": mock_page,
        "context": mock_context,
        "browser": mock_browser,
        "pw": mock_pw,
        "pw_instance": mock_pw_instance,
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
