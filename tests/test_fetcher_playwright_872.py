"""Failing RED-phase tests for #872: BrowserContentFetcher with Playwright BrowserContext.

AC mapping (from task #872):

  AC2   Constructor accepts a mock BrowserContext object
          (mock provides new_page as AsyncMock)
  AC3   fetch(url) happy path:
          context.new_page() → page.goto(url, wait_until="domcontentloaded") →
          page.content() → extract_content(html, url) → return string
  AC4   fetch(url) does NOT call check_sso_redirect — SSO extension handles
          auth transparently in persistent context
  AC5   page.close() awaited after successful fetch AND after exception
  AC6   isinstance(BrowserContentFetcher(ctx), ContentFetcher) is True;
          BrowserContentFetcher.fetch is an async coroutine function

All 11 tests FAIL at RED phase:
  - AC2/AC6: current __init__ stores arg as _cdp (not _context); constructor param
      is named 'cdp' not 'context' → AttributeError / AssertionError
  - AC3/AC4/AC5: current fetch() calls self._cdp._browser.contexts[0].new_page()
      which returns a non-awaitable MagicMock when passed a BrowserContext mock →
      TypeError before any assertion can be evaluated
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_URL = "https://contoso.sharepoint.com/sites/team"
_SAMPLE_HTML = "<html><body><h1>Dashboard</h1><p>Notes.</p></body></html>"
_SAMPLE_MARKDOWN = "# Dashboard\n\nNotes."


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_page() -> MagicMock:
    """Return a mock Playwright page with async goto/content/close methods."""
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=_SAMPLE_HTML)
    page.close = AsyncMock()
    return page


def _make_mock_context(page: MagicMock) -> MagicMock:
    """Return a mock Playwright BrowserContext with new_page wired to page."""
    ctx = MagicMock()
    ctx.new_page = AsyncMock(return_value=page)
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_BrowserContentFetcherPlaywright
# ---------------------------------------------------------------------------


class TestFromAC_BrowserContentFetcherPlaywright:
    """AC2-AC6: BrowserContentFetcher accepts Playwright BrowserContext directly."""

    # --- AC2: Constructor accepts BrowserContext ---

    def test_constructor_stores_context_not_cdp(self) -> None:
        """AC2: Constructor stores BrowserContext as _context (not _cdp)."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)
        fetcher = BrowserContentFetcher(ctx)

        # FAILS: current code stores as self._cdp; _context attribute does not exist
        assert fetcher._context is ctx  # type: ignore[attr-defined]

    # --- AC3: Happy path ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_opens_new_page_via_context(self) -> None:
        """AC3: fetch() calls context.new_page() directly (not via CDP chain)."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: current code calls self._cdp._browser.contexts[0].new_page() →
        # TypeError (non-awaitable MagicMock) before this assertion
        ctx.new_page.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_navigates_with_domcontentloaded(self) -> None:
        """AC3: fetch() calls page.goto(url, wait_until='domcontentloaded')."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: (a) crashes with TypeError on new_page; (b) even if reached,
        # current code calls goto(url) without wait_until keyword argument
        page.goto.assert_awaited_once_with(_TEST_URL, wait_until="domcontentloaded")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_calls_page_content(self) -> None:
        """AC3: fetch() calls page.content() to retrieve HTML."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: TypeError on new_page before reaching page.content()
        page.content.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_passes_html_and_url_to_extract_content(self) -> None:
        """AC3: fetch() passes (html, url) to extract_content()."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN) as mock_extract:
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: TypeError on new_page before extract_content is reached
        mock_extract.assert_called_once_with(_SAMPLE_HTML, _TEST_URL)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_returns_extract_content_result(self) -> None:
        """AC3: fetch() returns the string produced by extract_content()."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            result = await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: TypeError on new_page; never returns _SAMPLE_MARKDOWN
        assert result == _SAMPLE_MARKDOWN

    # --- AC4: No SSO redirect ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_does_not_call_check_sso_redirect(self) -> None:
        """AC4: fetch() never calls check_sso_redirect — SSO extension handles auth."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)
        ctx.check_sso_redirect = AsyncMock()  # present on context but must never be called

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: TypeError on new_page before reaching this assertion;
        # in GREEN, check_sso_redirect must remain uncalled
        ctx.check_sso_redirect.assert_not_called()

    # --- AC5: Page lifecycle ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_closes_page_after_successful_fetch(self) -> None:
        """AC5: page.close() is awaited after a successful fetch."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        ctx = _make_mock_context(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: TypeError on new_page before page is obtained or closed
        page.close.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_closes_page_on_exception(self) -> None:
        """AC5: page.close() is awaited even when an exception occurs during fetch."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        page.goto = AsyncMock(side_effect=RuntimeError("navigation timed out"))
        ctx = _make_mock_context(page)

        with (
            patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN),
            pytest.raises(RuntimeError),
        ):
            await BrowserContentFetcher(ctx).fetch(_TEST_URL)

        # FAILS: TypeError on new_page before page is obtained; close() never called
        page.close.assert_awaited_once()

    # --- AC6: Protocol compliance ---

    def test_satisfies_contentfetcher_protocol(self) -> None:
        """AC6: isinstance(BrowserContentFetcher(ctx), ContentFetcher) is True."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]
        from owlbear_knowledge.protocol import ContentFetcher

        page = _make_mock_page()
        ctx = _make_mock_context(page)
        fetcher = BrowserContentFetcher(ctx)

        assert isinstance(fetcher, ContentFetcher)

        # Verify new interface — constructor param must be 'context', not 'cdp'
        # FAILS: current __init__ signature has parameter named 'cdp'
        params = inspect.signature(BrowserContentFetcher.__init__).parameters
        assert "context" in params

    def test_fetch_is_async_coroutine_function(self) -> None:
        """AC6: BrowserContentFetcher.fetch is an async coroutine function."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        assert inspect.iscoroutinefunction(BrowserContentFetcher.fetch)

        # Verify new interface — constructor param must be 'context', not 'cdp'
        # FAILS: current __init__ signature has parameter named 'cdp'
        params = inspect.signature(BrowserContentFetcher.__init__).parameters
        assert "context" in params
