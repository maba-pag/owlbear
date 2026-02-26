"""Tests for browser_navigate tool — URL navigation with safety checks.

Covers: successful navigation returning title+URL, blocked URL raising
BlockedURLError, URL not in allowlist raising BlockedURLError, timeout
handling, and default config (no restrictions) succeeding.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, PropertyMock

import pytest

from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.safety import BlockedURLError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(*, title: str = "Example", url: str = "https://example.com") -> AsyncMock:
    """Build a mock Playwright Page with configurable title and url."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value=title)
    type(page).url = PropertyMock(return_value=url)
    return page


# ---------------------------------------------------------------------------
# Successful navigation
# ---------------------------------------------------------------------------


class TestBrowserNavigateSuccess:
    """Happy-path navigation returns formatted title + URL."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_title_and_url(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page(title="Example Domain", url="https://example.com")
        config = BrowserConfig()

        result = await browser_navigate("https://example.com", page=page, config=config)

        assert result == "Navigated to Example Domain (https://example.com)"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_calls_page_goto_with_url(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page()
        config = BrowserConfig()

        await browser_navigate("https://example.com", page=page, config=config)

        page.goto.assert_awaited_once_with("https://example.com", timeout=config.timeout_ms)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_default_config_no_restrictions(self) -> None:
        """Default BrowserConfig (empty allow/block lists) allows any URL."""
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page(title="Any Site", url="https://any-site.org")
        config = BrowserConfig()  # no blocklist, no allowlist

        result = await browser_navigate("https://any-site.org", page=page, config=config)

        assert "Any Site" in result
        assert "https://any-site.org" in result


# ---------------------------------------------------------------------------
# Blocked URL (blocklist)
# ---------------------------------------------------------------------------


class TestBrowserNavigateBlocked:
    """Navigation to blocked URLs raises BlockedURLError."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_blocked_url_raises(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page()
        config = BrowserConfig(blocked_urls=[r".*evil\.com.*"])

        with pytest.raises(BlockedURLError):
            await browser_navigate("https://evil.com/page", page=page, config=config)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_blocked_url_does_not_call_goto(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page()
        config = BrowserConfig(blocked_urls=[r".*evil\.com.*"])

        with pytest.raises(BlockedURLError):
            await browser_navigate("https://evil.com", page=page, config=config)

        page.goto.assert_not_awaited()


# ---------------------------------------------------------------------------
# Allowlist enforcement
# ---------------------------------------------------------------------------


class TestBrowserNavigateAllowlist:
    """When allowed_urls is set, only matching URLs are permitted."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_url_not_in_allowlist_raises(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page()
        config = BrowserConfig(allowed_urls=[r"^https://safe\.example\.com"])

        with pytest.raises(BlockedURLError):
            await browser_navigate("https://other.com", page=page, config=config)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_url_in_allowlist_succeeds(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page(title="Safe Page", url="https://safe.example.com/docs")
        config = BrowserConfig(allowed_urls=[r"^https://safe\.example\.com"])

        result = await browser_navigate("https://safe.example.com/docs", page=page, config=config)

        assert "Safe Page" in result


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------


class TestBrowserNavigateTimeout:
    """Timeout from page.goto surfaces as TimeoutError."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_timeout_raises_timeout_error(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page()
        page.goto = AsyncMock(side_effect=TimeoutError("Navigation timeout"))
        config = BrowserConfig(timeout_ms=5_000)

        with pytest.raises(TimeoutError, match="Navigation timeout"):
            await browser_navigate("https://slow.example.com", page=page, config=config)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_passes_config_timeout_to_goto(self) -> None:
        from owlbear.tools.browser.actions import browser_navigate

        page = _make_page()
        config = BrowserConfig(timeout_ms=15_000)

        await browser_navigate("https://example.com", page=page, config=config)

        page.goto.assert_awaited_once_with("https://example.com", timeout=15_000)
