"""Tests for WebSearchToolset — mock ddgs and httpx.

Covers web_search, web_read, URL safety checks, tool registration,
and constructor parameters.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from owlbear.tools.web_search import WebSearchToolset

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_RESULTS = [
    {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
    {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
    {"title": "Result 3", "href": "https://example.com/3", "body": "Snippet 3"},
]


# ---------------------------------------------------------------------------
# Fixtures — mocked external dependencies
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ddgs() -> MagicMock:
    """Mock DDGS class from duckduckgo_search."""
    instance = MagicMock()
    instance.text.return_value = list(SAMPLE_RESULTS)
    mock_cls = MagicMock(return_value=instance)
    with patch("owlbear.tools.web_search.DDGS", mock_cls):
        yield mock_cls


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """Mock httpx.AsyncClient for web_read tests."""
    response = MagicMock()
    response.status_code = 200
    response.text = "<html><body><p>Hello world</p></body></html>"
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.get.return_value = response

    cm = AsyncMock()
    cm.__aenter__.return_value = client
    cm.__aexit__.return_value = False

    with patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=cm):
        yield client


@pytest.fixture
def toolset() -> WebSearchToolset:
    """WebSearchToolset with default config."""
    return WebSearchToolset()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Verify toolset registers the expected tools."""

    def test_registers_two_tools(self, toolset: WebSearchToolset) -> None:
        assert len(toolset.tools) == 2

    def test_tool_names(self, toolset: WebSearchToolset) -> None:
        names = set(toolset.tools.keys())
        assert names == {"web_search", "web_read"}


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """Verify constructor accepts blocked_urls and allowed_urls lists."""

    def test_default_empty_lists(self) -> None:
        ts = WebSearchToolset()
        assert ts._blocked_urls == []
        assert ts._allowed_urls == []

    def test_accepts_blocked_urls(self) -> None:
        ts = WebSearchToolset(blocked_urls=[r".*evil\.com.*"])
        assert len(ts._blocked_urls) == 1
        assert ts._blocked_urls[0].pattern == r".*evil\.com.*"

    def test_accepts_allowed_urls(self) -> None:
        ts = WebSearchToolset(allowed_urls=[r".*safe\.org.*"])
        assert len(ts._allowed_urls) == 1
        assert ts._allowed_urls[0].pattern == r".*safe\.org.*"

    def test_accepts_both_lists(self) -> None:
        ts = WebSearchToolset(
            blocked_urls=[r".*evil\.com.*"],
            allowed_urls=[r".*safe\.org.*"],
        )
        assert len(ts._blocked_urls) == 1
        assert ts._blocked_urls[0].pattern == r".*evil\.com.*"
        assert len(ts._allowed_urls) == 1
        assert ts._allowed_urls[0].pattern == r".*safe\.org.*"


# ---------------------------------------------------------------------------
# URL safety check
# ---------------------------------------------------------------------------


class TestCheckURL:
    """Verify _check_url against blocked/allowed patterns."""

    def test_allows_with_no_restrictions(self) -> None:
        ts = WebSearchToolset()
        ts._check_url("https://anything.com")  # Should not raise

    def test_blocks_matching_blocked_pattern(self) -> None:
        ts = WebSearchToolset(blocked_urls=[r".*evil\.com.*"])
        with pytest.raises(ValueError, match="blocked"):
            ts._check_url("https://evil.com/page")

    def test_allows_non_matching_blocked(self) -> None:
        ts = WebSearchToolset(blocked_urls=[r".*evil\.com.*"])
        ts._check_url("https://example.com")  # Should not raise

    def test_blocks_when_not_in_allowlist(self) -> None:
        ts = WebSearchToolset(allowed_urls=[r".*example\.com.*"])
        with pytest.raises(ValueError, match="not in allowed"):
            ts._check_url("https://other.com")

    def test_allows_when_in_allowlist(self) -> None:
        ts = WebSearchToolset(allowed_urls=[r".*example\.com.*"])
        ts._check_url("https://example.com/page")  # Should not raise

    def test_blocklist_takes_precedence_over_allowlist(self) -> None:
        ts = WebSearchToolset(
            blocked_urls=[r".*evil\.com.*"],
            allowed_urls=[r".*evil\.com.*"],
        )
        with pytest.raises(ValueError, match="blocked"):
            ts._check_url("https://evil.com")


# ---------------------------------------------------------------------------
# web_search
# ---------------------------------------------------------------------------


class TestWebSearch:
    """Verify web_search tool behavior."""

    @pytest.mark.usefixtures("mock_ddgs")
    @pytest.mark.asyncio
    async def test_returns_numbered_markdown(self) -> None:
        """web_search returns numbered markdown with title, URL, snippet."""
        ts = WebSearchToolset()
        result = await ts._web_search("test query")
        assert "1. [Result 1](https://example.com/1)" in result
        assert "Snippet 1" in result
        assert "2. [Result 2](https://example.com/2)" in result
        assert "3. [Result 3](https://example.com/3)" in result

    @pytest.mark.asyncio
    async def test_empty_results_returns_no_results(
        self, mock_ddgs: MagicMock,
    ) -> None:
        """Empty DDGS results return 'No results found'."""
        mock_ddgs.return_value.text.return_value = []
        ts = WebSearchToolset()
        result = await ts._web_search("nothing here")
        assert result == "No results found for: nothing here"

    @pytest.mark.asyncio
    async def test_calls_ddgs_with_correct_params(
        self, mock_ddgs: MagicMock,
    ) -> None:
        """DDGS().text() is called with keywords and max_results."""
        ts = WebSearchToolset()
        await ts._web_search("test query", num_results=3)
        mock_ddgs.return_value.text.assert_called_once_with(
            keywords="test query", max_results=3,
        )

    @pytest.mark.asyncio
    async def test_uses_asyncio_to_thread(self) -> None:
        """web_search offloads the blocking DDGS call via asyncio.to_thread."""
        instance = MagicMock()
        instance.text.return_value = list(SAMPLE_RESULTS)
        mock_cls = MagicMock(return_value=instance)

        with (
            patch("owlbear.tools.web_search.DDGS", mock_cls),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.return_value = list(SAMPLE_RESULTS)
            ts = WebSearchToolset()
            await ts._web_search("test")
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_blocked_urls(self, mock_ddgs: MagicMock) -> None:
        """Blocked URLs are excluded from results."""
        mock_ddgs.return_value.text.return_value = [
            {"title": "Good", "href": "https://safe.com/1", "body": "Safe content"},
            {"title": "Bad", "href": "https://evil.com/hack", "body": "Evil"},
            {"title": "Also Good", "href": "https://safe.com/2", "body": "Also safe"},
        ]
        ts = WebSearchToolset(blocked_urls=[r".*evil\.com.*"])
        result = await ts._web_search("test")
        assert "evil.com" not in result
        assert "1. [Good](https://safe.com/1)" in result
        assert "2. [Also Good](https://safe.com/2)" in result

    @pytest.mark.asyncio
    async def test_all_results_blocked_returns_no_results(
        self, mock_ddgs: MagicMock,
    ) -> None:
        """All results blocked returns 'No results found'."""
        mock_ddgs.return_value.text.return_value = [
            {"title": "Bad 1", "href": "https://evil.com/1", "body": "Evil 1"},
            {"title": "Bad 2", "href": "https://evil.com/2", "body": "Evil 2"},
        ]
        ts = WebSearchToolset(blocked_urls=[r".*evil\.com.*"])
        result = await ts._web_search("test")
        assert result == "No results found for: test"


# ---------------------------------------------------------------------------
# web_read
# ---------------------------------------------------------------------------


class TestWebRead:
    """Verify web_read tool behavior."""

    @pytest.mark.asyncio
    async def test_fetches_and_extracts_content(
        self, mock_httpx_client: AsyncMock,
    ) -> None:
        """web_read fetches URL via httpx and extracts content with trafilatura."""
        with patch("owlbear.tools.web_search.trafilatura") as mock_traf:
            mock_traf.extract.return_value = "Extracted content from page"
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com")
            assert result == "Extracted content from page"
            mock_httpx_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_blocked_url_raises_valueerror(self) -> None:
        """web_read with blocked URL raises ValueError."""
        ts = WebSearchToolset(blocked_urls=[r".*evil\.com.*"])
        with pytest.raises(ValueError, match="blocked"):
            await ts._web_read("https://evil.com/page")

    @pytest.mark.asyncio
    async def test_httpx_error_returns_error_message(self) -> None:
        """web_read with httpx error returns error message string."""
        client = AsyncMock()
        client.get.side_effect = httpx.HTTPError("Connection refused")

        cm = AsyncMock()
        cm.__aenter__.return_value = client
        cm.__aexit__.return_value = False

        with patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=cm):
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com")
            assert "error" in result.lower()

    @pytest.mark.usefixtures("mock_httpx_client")
    @pytest.mark.asyncio
    async def test_empty_extraction_returns_raw_fallback(
        self,
    ) -> None:
        """web_read with empty trafilatura extraction returns raw HTML fallback."""
        with patch("owlbear.tools.web_search.trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com")
            assert "<html>" in result  # raw HTML returned as fallback

    @pytest.mark.asyncio
    async def test_web_read_passes_timeout_30(
        self, mock_httpx_client: AsyncMock,
    ) -> None:
        """httpx.get is called with timeout=30."""
        with patch("owlbear.tools.web_search.trafilatura") as mock_traf:
            mock_traf.extract.return_value = "content"
            ts = WebSearchToolset()
            await ts._web_read("https://example.com")
            mock_httpx_client.get.assert_called_once_with(
                "https://example.com", timeout=30, follow_redirects=True,
            )

    @pytest.mark.asyncio
    async def test_web_read_respects_allowlist(self) -> None:
        """Rejects URL not in allowed_urls when set."""
        ts = WebSearchToolset(allowed_urls=[r".*example\.com.*"])
        with pytest.raises(ValueError, match="not in allowed"):
            await ts._web_read("https://other.com/page")

    @pytest.mark.asyncio
    async def test_web_read_handles_fetch_timeout(self) -> None:
        """httpx.TimeoutException returns 'Timeout fetching {url}'."""
        client = AsyncMock()
        client.get.side_effect = httpx.TimeoutException("timed out")

        cm = AsyncMock()
        cm.__aenter__.return_value = client
        cm.__aexit__.return_value = False

        with patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=cm):
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com")
            assert result == "Timeout fetching https://example.com"

    @pytest.mark.asyncio
    async def test_web_read_handles_http_error(self) -> None:
        """404/500 returns 'HTTP {status}: {url}'."""
        response = MagicMock()
        response.status_code = 404

        client = AsyncMock()
        client.get.return_value = response
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=response,
        )

        cm = AsyncMock()
        cm.__aenter__.return_value = client
        cm.__aexit__.return_value = False

        with patch("owlbear.tools.web_search.httpx.AsyncClient", return_value=cm):
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com/missing")
            assert result == "HTTP 404: https://example.com/missing"

    @pytest.mark.usefixtures("mock_httpx_client")
    @pytest.mark.asyncio
    async def test_web_read_truncates_long_content(self) -> None:
        """Output capped at max_length characters."""
        with patch("owlbear.tools.web_search.trafilatura") as mock_traf:
            mock_traf.extract.return_value = "x" * 200
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com", max_length=100)
            assert len(result) == 100

    @pytest.mark.usefixtures("mock_httpx_client")
    @pytest.mark.asyncio
    async def test_web_read_trafilatura_fallback(self) -> None:
        """If trafilatura returns None, return raw text truncated."""
        with patch("owlbear.tools.web_search.trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            ts = WebSearchToolset()
            result = await ts._web_read("https://example.com", max_length=20)
            # Raw HTML from mock: "<html><body><p>Hello world</p></body></html>"
            assert len(result) <= 20
            assert result.startswith("<html>")


# ---------------------------------------------------------------------------
# web_search — additional gap tests
# ---------------------------------------------------------------------------


class TestWebSearchGaps:
    """Additional web_search tests for reviewer-identified gaps."""

    @pytest.mark.asyncio
    async def test_web_search_respects_allowlist(
        self, mock_ddgs: MagicMock,
    ) -> None:
        """Only results matching allowed_urls returned when set."""
        mock_ddgs.return_value.text.return_value = [
            {"title": "Good", "href": "https://example.com/1", "body": "Good"},
            {"title": "Bad", "href": "https://other.com/2", "body": "Bad"},
        ]
        ts = WebSearchToolset(allowed_urls=[r".*example\.com.*"])
        result = await ts._web_search("test")
        assert "example.com" in result
        assert "other.com" not in result

    @pytest.mark.asyncio
    async def test_web_search_handles_rate_limit(self) -> None:
        """Catches RatelimitException, returns informative error string."""
        RateLimitError = type("RatelimitException", (Exception,), {})  # noqa: N806

        instance = MagicMock()
        instance.text.side_effect = RateLimitError("rate limited")
        mock_cls = MagicMock(return_value=instance)

        with (
            patch("owlbear.tools.web_search.DDGS", mock_cls),
            patch("owlbear.tools.web_search._RatelimitException", RateLimitError),
        ):
            ts = WebSearchToolset()
            result = await ts._web_search("test")
            assert result == "Rate limited. Try again in a few seconds."

    @pytest.mark.asyncio
    async def test_web_search_num_results_param(
        self, mock_ddgs: MagicMock,
    ) -> None:
        """Passes num_results to DDGS.text() max_results param."""
        ts = WebSearchToolset()
        await ts._web_search("test", num_results=10)
        mock_ddgs.return_value.text.assert_called_once_with(
            keywords="test", max_results=10,
        )

    @pytest.mark.asyncio
    async def test_ddgs_import_guard(self) -> None:
        """When ddgs not installed, import error raised at tool call time."""
        with patch("owlbear.tools.web_search.DDGS", None):
            ts = WebSearchToolset()
            with pytest.raises(ImportError, match="duckduckgo_search"):
                await ts._web_search("test")
