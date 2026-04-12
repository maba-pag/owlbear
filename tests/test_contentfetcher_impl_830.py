"""Failing RED-phase tests for #830: BrowserContentFetcher + HttpxContentFetcher.

AC mapping (from tasks #830 and #841):

  AC-B1  BrowserContentFetcher importable from owlbear_browser.fetcher
  AC-B2  isinstance(obj, ContentFetcher) is True for BrowserContentFetcher
  AC-B3  fetch(url) delegates: CDPConnectionManager._browser.contexts[0].new_page()
           → page.goto(url) → check_sso_redirect(page) → page.content()
           → extract_content(html, url) → return markdown str
  AC-B4  SSO redirect detected → raises AuthenticationRequired
  AC-B5  page.close() always called after successful fetch
  AC-B6  page.close() always called even when an error is raised during fetch

  AC-H1  HttpxContentFetcher importable from owlbear_knowledge.fetcher
  AC-H2  isinstance(obj, ContentFetcher) is True for HttpxContentFetcher
  AC-H3  fetch(url) delegates to httpx.AsyncClient.get(url)
  AC-H4  Non-2xx HTTP response raises httpx.HTTPStatusError
  AC-H5  fetch() returns response.text as str

All 18 tests FAIL at RED phase — neither fetcher.py file exists yet.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_URL = "https://contoso.sharepoint.com/sites/team"
_SSO_URL = "https://login.microsoftonline.com/tenant/oauth2"
_SAMPLE_HTML = "<html><body><h1>Project Home</h1><p>Meeting notes.</p></body></html>"
_SAMPLE_MARKDOWN = "# Project Home\n\nMeeting notes."


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_page() -> MagicMock:
    """Return a mock Playwright page with async navigate/content/close methods."""
    page = MagicMock()
    page.url = _TEST_URL
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=_SAMPLE_HTML)
    page.close = AsyncMock()
    page.query_selector = MagicMock(return_value=None)
    return page


def _make_mock_cdp(page: MagicMock) -> MagicMock:
    """Return a mock CDPConnectionManager wired with one context/page."""
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.contexts = [context]
    cdp = MagicMock()
    cdp._browser = browser
    cdp.check_sso_redirect = AsyncMock()  # no redirect by default
    return cdp


# ---------------------------------------------------------------------------
# TestFromAC_BrowserContentFetcher
# ---------------------------------------------------------------------------


class TestFromAC_BrowserContentFetcher:
    """AC-B1..B6: BrowserContentFetcher wraps CDPConnectionManager for authenticated fetch."""

    # --- AC-B1: importable ---

    def test_browser_fetcher_module_is_importable(self) -> None:
        """AC-B1: BrowserContentFetcher is importable from owlbear_browser.fetcher."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]  # noqa: F401

    # --- AC-B2: protocol satisfaction ---

    def test_satisfies_contentfetcher_protocol(self) -> None:
        """AC-B2: isinstance(BrowserContentFetcher(...), ContentFetcher) is True."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]
        from owlbear_knowledge.protocol import ContentFetcher

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)
        fetcher = BrowserContentFetcher(cdp)

        assert isinstance(fetcher, ContentFetcher)

    def test_fetch_method_is_async_coroutine(self) -> None:
        """AC-B2: BrowserContentFetcher.fetch is an async coroutine function."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        assert inspect.iscoroutinefunction(BrowserContentFetcher.fetch)

    # --- AC-B3: delegation chain ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_opens_new_page_from_browser_context(self) -> None:
        """AC-B3: fetch() calls cdp._browser.contexts[0].new_page()."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            await fetcher.fetch(_TEST_URL)

        cdp._browser.contexts[0].new_page.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_navigates_to_url_via_goto(self) -> None:
        """AC-B3: fetch() calls page.goto(url) with the requested URL."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            await fetcher.fetch(_TEST_URL)

        page.goto.assert_awaited_once_with(_TEST_URL)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_calls_check_sso_redirect_with_page(self) -> None:
        """AC-B3: fetch() calls cdp.check_sso_redirect(page) after navigation."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            await fetcher.fetch(_TEST_URL)

        cdp.check_sso_redirect.assert_awaited_once_with(page)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_calls_page_content(self) -> None:
        """AC-B3: fetch() calls page.content() to retrieve page HTML."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            await fetcher.fetch(_TEST_URL)

        page.content.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_passes_html_and_url_to_extract_content(self) -> None:
        """AC-B3: fetch() passes (html, url) to extract_content."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch(
            "owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN
        ) as mock_extract:
            fetcher = BrowserContentFetcher(cdp)
            await fetcher.fetch(_TEST_URL)

        mock_extract.assert_called_once_with(_SAMPLE_HTML, _TEST_URL)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_returns_markdown_string_from_extract_content(self) -> None:
        """AC-B3: fetch() returns the string produced by extract_content."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            result = await fetcher.fetch(_TEST_URL)

        assert result == _SAMPLE_MARKDOWN

    # --- AC-B4: SSO detection ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sso_redirect_raises_authentication_required(self) -> None:
        """AC-B4: AuthenticationRequired from check_sso_redirect is propagated by fetch()."""
        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        page.url = _SSO_URL
        cdp = _make_mock_cdp(page)
        cdp.check_sso_redirect = AsyncMock(
            side_effect=AuthenticationRequired("SSO session expired: login redirect")
        )

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            with pytest.raises(AuthenticationRequired):
                await fetcher.fetch(_TEST_URL)

    # --- AC-B5/B6: page lifecycle ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_page_closed_after_successful_fetch(self) -> None:
        """AC-B5: page.close() is awaited after a successful fetch()."""
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            await fetcher.fetch(_TEST_URL)

        page.close.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_page_closed_even_when_error_is_raised(self) -> None:
        """AC-B6: page.close() is awaited even when an exception escapes fetch()."""
        from owlbear_browser._errors import AuthenticationRequired
        from owlbear_browser.fetcher import BrowserContentFetcher  # type: ignore[import]

        page = _make_mock_page()
        cdp = _make_mock_cdp(page)
        cdp.check_sso_redirect = AsyncMock(
            side_effect=AuthenticationRequired("login redirect")
        )

        with patch("owlbear_browser.fetcher.extract_content", return_value=_SAMPLE_MARKDOWN):
            fetcher = BrowserContentFetcher(cdp)
            with pytest.raises(AuthenticationRequired):
                await fetcher.fetch(_TEST_URL)

        page.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# TestFromAC_HttpxContentFetcher
# ---------------------------------------------------------------------------


class TestFromAC_HttpxContentFetcher:
    """AC-H1..H5: HttpxContentFetcher wraps httpx.AsyncClient for unauthenticated fetch."""

    # --- AC-H1: importable ---

    def test_httpx_fetcher_module_is_importable(self) -> None:
        """AC-H1: HttpxContentFetcher is importable from owlbear_knowledge.fetcher."""
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]  # noqa: F401

    # --- AC-H2: protocol satisfaction ---

    def test_satisfies_contentfetcher_protocol(self) -> None:
        """AC-H2: isinstance(HttpxContentFetcher(), ContentFetcher) is True."""
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]
        from owlbear_knowledge.protocol import ContentFetcher

        fetcher = HttpxContentFetcher()

        assert isinstance(fetcher, ContentFetcher)

    def test_fetch_method_is_async_coroutine(self) -> None:
        """AC-H2: HttpxContentFetcher.fetch is an async coroutine function."""
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]

        assert inspect.iscoroutinefunction(HttpxContentFetcher.fetch)

    # --- AC-H3: delegation ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_delegates_to_httpx_async_client_get(self) -> None:
        """AC-H3: fetch(url) calls httpx.AsyncClient.get(url)."""
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]

        mock_response = MagicMock()
        mock_response.text = "page content"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("owlbear_knowledge.fetcher.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            fetcher = HttpxContentFetcher()
            await fetcher.fetch(_TEST_URL)

        mock_client.get.assert_awaited_once_with(_TEST_URL)

    # --- AC-H5: return value ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_returns_response_text(self) -> None:
        """AC-H5: fetch() returns response.text as a str."""
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]

        mock_response = MagicMock()
        mock_response.text = "response body text"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("owlbear_knowledge.fetcher.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            fetcher = HttpxContentFetcher()
            result = await fetcher.fetch(_TEST_URL)

        assert result == "response body text"

    # --- AC-H4: non-2xx error ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_2xx_response_raises_http_status_error(self) -> None:
        """AC-H4: Non-2xx HTTP response propagates as httpx.HTTPStatusError."""
        import httpx
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found", request=mock_request, response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("owlbear_knowledge.fetcher.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            fetcher = HttpxContentFetcher()
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch(_TEST_URL)

    # --- Edge: empty URL forwarded without validation ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_with_empty_url_passes_through_to_httpx(self) -> None:
        """Edge: empty-string URL is forwarded to httpx without ContentFetcher-level validation."""
        from owlbear_knowledge.fetcher import HttpxContentFetcher  # type: ignore[import]

        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("owlbear_knowledge.fetcher.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            fetcher = HttpxContentFetcher()
            await fetcher.fetch("")

        mock_client.get.assert_awaited_once_with("")
