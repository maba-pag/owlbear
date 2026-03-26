"""Tests for browser content extraction tools — read_text, screenshot.

Covers: browser_read_text (full page, selector, truncation, whitespace)
and browser_screenshot (full page, element, base64 encoding).
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _disable_wrap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable content wrapping so tests verify raw extraction logic."""
    monkeypatch.setenv("OWLBEAR_WRAP_WEB_CONTENT", "false")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page() -> AsyncMock:
    """Build a mock Playwright Page with common async methods."""
    page = AsyncMock()
    page.inner_text = AsyncMock(return_value="Hello world")
    page.wait_for_selector = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nfake")
    return page


# ===========================================================================
# browser_read_text
# ===========================================================================


class TestBrowserReadTextFullPage:
    """browser_read_text with selector=None reads the full page body."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_body_inner_text(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "Page content here"

        result = await browser_read_text(page=page)

        assert result == "Page content here"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_inner_text_on_body(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        await browser_read_text(page=page)

        page.inner_text.assert_awaited_once_with("body")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_does_not_call_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        await browser_read_text(page=page)

        page.wait_for_selector.assert_not_awaited()


class TestBrowserReadTextSelector:
    """browser_read_text with a selector reads a specific element."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_element_text(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "Element text"

        result = await browser_read_text(page=page, selector="#content")

        assert result == "Element text"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        await browser_read_text(page=page, selector=".article")

        page.wait_for_selector.assert_awaited_once_with(".article")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_inner_text_with_selector(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        await browser_read_text(page=page, selector="div.main")

        page.inner_text.assert_awaited_once_with("div.main")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_missing_selector_propagates_error(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout 30000ms exceeded")

        with pytest.raises(TimeoutError, match="Timeout"):
            await browser_read_text(page=page, selector="#missing")


class TestBrowserReadTextTruncation:
    """browser_read_text truncates long text and strips whitespace."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_text_under_max_length_returned_as_is(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "Short text"

        result = await browser_read_text(page=page, max_length=5000)

        assert result == "Short text"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_long_text_truncated_with_suffix(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "A" * 6000

        result = await browser_read_text(page=page, max_length=100)

        assert result.endswith("... [truncated]")
        assert len(result) == 100 + len("... [truncated]")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_truncation_cuts_at_max_length(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "B" * 200

        result = await browser_read_text(page=page, max_length=50)

        # First 50 chars + suffix
        assert result.startswith("B" * 50)
        assert result == "B" * 50 + "... [truncated]"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_custom_max_length(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "C" * 300

        result = await browser_read_text(page=page, max_length=10)

        assert result == "C" * 10 + "... [truncated]"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_whitespace_stripped(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "  \n  Hello world  \n  "

        result = await browser_read_text(page=page)

        assert result == "Hello world"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_exact_max_length_not_truncated(self):
        from owlbear.tools.browser.actions import browser_read_text

        page = _make_page()
        page.inner_text.return_value = "D" * 100

        result = await browser_read_text(page=page, max_length=100)

        assert result == "D" * 100
        assert "truncated" not in result


# ===========================================================================
# browser_screenshot
# ===========================================================================


class TestBrowserScreenshotFullPage:
    """browser_screenshot with selector=None captures the full page."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_base64_string(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        png_bytes = b"\x89PNG\r\n\x1a\nfakedata"
        page.screenshot.return_value = png_bytes

        result = await browser_screenshot(page=page)

        expected = base64.b64encode(png_bytes).decode("ascii")
        assert result == expected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_page_screenshot_full_page_true(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        await browser_screenshot(page=page)

        page.screenshot.assert_awaited_once_with(full_page=True)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_full_page_false_passed_through(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        await browser_screenshot(page=page, full_page=False)

        page.screenshot.assert_awaited_once_with(full_page=False)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_does_not_call_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        await browser_screenshot(page=page)

        page.wait_for_selector.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returned_string_is_valid_base64(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        page.screenshot.return_value = b"some png bytes here"

        result = await browser_screenshot(page=page)

        # Should not raise
        decoded = base64.b64decode(result)
        assert decoded == b"some png bytes here"


class TestBrowserScreenshotElement:
    """browser_screenshot with a selector captures an element screenshot."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_base64_of_element_screenshot(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        locator = AsyncMock()
        locator.screenshot = AsyncMock(return_value=b"element-png")
        page.wait_for_selector.return_value = locator

        result = await browser_screenshot(page=page, selector="#chart")

        expected = base64.b64encode(b"element-png").decode("ascii")
        assert result == expected

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_wait_for_selector(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        locator = AsyncMock()
        locator.screenshot = AsyncMock(return_value=b"img")
        page.wait_for_selector.return_value = locator

        await browser_screenshot(page=page, selector="canvas.graph")

        page.wait_for_selector.assert_awaited_once_with("canvas.graph")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_locator_screenshot(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        locator = AsyncMock()
        locator.screenshot = AsyncMock(return_value=b"element-bytes")
        page.wait_for_selector.return_value = locator

        await browser_screenshot(page=page, selector="img.hero")

        locator.screenshot.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_does_not_call_page_screenshot(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        locator = AsyncMock()
        locator.screenshot = AsyncMock(return_value=b"el")
        page.wait_for_selector.return_value = locator

        await browser_screenshot(page=page, selector="div.box")

        page.screenshot.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_missing_selector_propagates_error(self):
        from owlbear.tools.browser.actions import browser_screenshot

        page = _make_page()
        page.wait_for_selector.side_effect = TimeoutError("Timeout 30000ms exceeded")

        with pytest.raises(TimeoutError, match="Timeout"):
            await browser_screenshot(page=page, selector="#missing")
