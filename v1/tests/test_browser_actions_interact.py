"""Tests for browser interaction tools — click, type, select.

Covers: browser_click, browser_type, browser_select — verifies correct
Playwright API calls, wait-for-selector behavior, error handling on
missing elements, and fill vs type distinction for browser_type.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page() -> AsyncMock:
    """Build a mock Playwright Page with common async methods."""
    page = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()  # should NOT be called — we use fill
    page.select_option = AsyncMock()
    return page


# ===========================================================================
# browser_click
# ===========================================================================


class TestBrowserClick:
    """browser_click waits for the selector, clicks it, returns confirmation."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_confirmation_string(self):
        from owlbear.tools.browser.actions import browser_click

        page = _make_page()
        result = await browser_click("#submit-btn", page=page)

        assert result == "Clicked #submit-btn"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_click

        page = _make_page()
        await browser_click("button.primary", page=page)

        page.wait_for_selector.assert_awaited_once_with("button.primary")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_page_click(self):
        from owlbear.tools.browser.actions import browser_click

        page = _make_page()
        await browser_click("a.link", page=page)

        page.click.assert_awaited_once_with("a.link")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_timeout_propagates(self):
        from owlbear.tools.browser.actions import browser_click

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout 30000ms exceeded")

        with pytest.raises(TimeoutError, match="Timeout"):
            await browser_click("#missing", page=page)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_click_not_called_on_timeout(self):
        """If wait_for_selector fails, click should never be called."""
        from owlbear.tools.browser.actions import browser_click

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            await browser_click("#missing", page=page)

        page.click.assert_not_awaited()


# ===========================================================================
# browser_type
# ===========================================================================


class TestBrowserType:
    """browser_type waits for selector, fills text, returns confirmation."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_confirmation_string(self):
        from owlbear.tools.browser.actions import browser_type

        page = _make_page()
        result = await browser_type("#email", "user@example.com", page=page)

        assert result == "Typed 'user@example.com' into #email"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_type

        page = _make_page()
        await browser_type("input[name='q']", "search query", page=page)

        page.wait_for_selector.assert_awaited_once_with("input[name='q']")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_page_fill_not_type(self):
        """browser_type must use page.fill (clears + sets) not page.type."""
        from owlbear.tools.browser.actions import browser_type

        page = _make_page()
        await browser_type("#name", "Alice", page=page)

        page.fill.assert_awaited_once_with("#name", "Alice")
        page.type.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_timeout_propagates(self):
        from owlbear.tools.browser.actions import browser_type

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout 30000ms exceeded")

        with pytest.raises(TimeoutError, match="Timeout"):
            await browser_type("#missing", "text", page=page)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fill_not_called_on_timeout(self):
        """If wait_for_selector fails, fill should never be called."""
        from owlbear.tools.browser.actions import browser_type

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            await browser_type("#missing", "text", page=page)

        page.fill.assert_not_awaited()


# ===========================================================================
# browser_select
# ===========================================================================


class TestBrowserSelect:
    """browser_select waits for selector, selects option, returns confirmation."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_confirmation_string(self):
        from owlbear.tools.browser.actions import browser_select

        page = _make_page()
        result = await browser_select("#country", "us", page=page)

        assert result == "Selected 'us' in #country"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_select

        page = _make_page()
        await browser_select("select.lang", "en", page=page)

        page.wait_for_selector.assert_awaited_once_with("select.lang")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_page_select_option(self):
        from owlbear.tools.browser.actions import browser_select

        page = _make_page()
        await browser_select("#size", "large", page=page)

        page.select_option.assert_awaited_once_with("#size", "large")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_timeout_propagates(self):
        from owlbear.tools.browser.actions import browser_select

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout 30000ms exceeded")

        with pytest.raises(TimeoutError, match="Timeout"):
            await browser_select("#missing", "val", page=page)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_select_option_not_called_on_timeout(self):
        """If wait_for_selector fails, select_option should never be called."""
        from owlbear.tools.browser.actions import browser_select

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            await browser_select("#missing", "val", page=page)

        page.select_option.assert_not_awaited()
