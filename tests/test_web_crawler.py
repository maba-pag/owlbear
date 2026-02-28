"""Tests for WebCrawler — async BFS crawl with mocked browser interactions.

Covers: CrawlPage/CrawlResult models, WebCrawler init, crawl() return type,
max_depth, max_pages, same_domain_only, robots.txt compliance, rate limiting,
URL dedup, error handling.  All browser interactions are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.tools.browser.content_extractor import ExtractionResult
from owlbear.tools.browser.crawl_config import CrawlConfig
from owlbear.tools.browser.crawler import CrawlPage, CrawlResult, WebCrawler

_SEED = ["https://example.com"]
_MODULE = "owlbear.tools.browser.crawler"
_DEFAULT_HTML = "<html><body>Hello</body></html>"
_DEFAULT_EXTRACTION = ExtractionResult(
    text="extracted text",
    title="Test Page",
    metadata={"title": "Test Page"},
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_page():
    """Mock Playwright page with async goto() and content()."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=_DEFAULT_HTML)
    return page


@pytest.fixture
def mock_browser_manager(mock_page):
    """Mock BrowserManager whose .page attribute returns mock_page."""
    mgr = MagicMock()
    mgr.page = mock_page
    return mgr


# ---------------------------------------------------------------------------
# CrawlPage model
# ---------------------------------------------------------------------------


class TestCrawlPageModel:
    """CrawlPage is a frozen Pydantic model with url, content, title, metadata."""

    def test_fields_present(self):
        page = CrawlPage(
            url="https://example.com",
            content="body",
            title="T",
            metadata={"k": "v"},
        )
        assert page.url == "https://example.com"
        assert page.content == "body"
        assert page.title == "T"
        assert page.metadata == {"k": "v"}

    def test_frozen(self):
        page = CrawlPage(url="https://example.com", content="body")
        with pytest.raises(ValidationError):
            page.url = "changed"  # type: ignore[misc]

    def test_title_defaults_to_none(self):
        page = CrawlPage(url="https://example.com", content="body")
        assert page.title is None

    def test_metadata_defaults_to_empty_dict(self):
        page = CrawlPage(url="https://example.com", content="body")
        assert page.metadata == {}


# ---------------------------------------------------------------------------
# CrawlResult model
# ---------------------------------------------------------------------------


class TestCrawlResultModel:
    """CrawlResult is a frozen Pydantic model with pages, total_pages, errors."""

    def test_fields_present(self):
        page = CrawlPage(url="https://example.com", content="body")
        result = CrawlResult(pages=[page], total_pages=1, errors=["err1"])
        assert len(result.pages) == 1
        assert result.total_pages == 1
        assert result.errors == ["err1"]

    def test_frozen(self):
        result = CrawlResult(pages=[], total_pages=0)
        with pytest.raises(ValidationError):
            result.total_pages = 5  # type: ignore[misc]

    def test_errors_defaults_to_empty_list(self):
        result = CrawlResult(pages=[], total_pages=0)
        assert result.errors == []


# ---------------------------------------------------------------------------
# WebCrawler init
# ---------------------------------------------------------------------------


class TestWebCrawlerInit:
    """WebCrawler accepts a BrowserManager instance."""

    def test_accepts_browser_manager(self, mock_browser_manager):
        crawler = WebCrawler(mock_browser_manager)
        assert crawler._browser_manager is mock_browser_manager


# ---------------------------------------------------------------------------
# Crawl — basic behavior
# ---------------------------------------------------------------------------


class TestWebCrawlerCrawlBasic:
    """crawl() returns CrawlResult with correct structure and content."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_returns_crawl_result(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(seed_urls=_SEED, delay_seconds=0, respect_robots=False)
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert isinstance(result, CrawlResult)

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_crawl_result_contains_page_data(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(seed_urls=_SEED, delay_seconds=0, respect_robots=False)
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert len(result.pages) == 1
        assert result.pages[0].url == "https://example.com"
        assert result.pages[0].content == "extracted text"
        assert result.pages[0].title == "Test Page"

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_total_pages_matches_page_count(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(seed_urls=_SEED, delay_seconds=0, respect_robots=False)
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == len(result.pages) == 1

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_multiple_seed_urls(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(
            seed_urls=["https://example.com", "https://example.com/about"],
            delay_seconds=0,
            respect_robots=False,
            same_domain_only=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 2


# ---------------------------------------------------------------------------
# Max depth
# ---------------------------------------------------------------------------


class TestMaxDepth:
    """Respects max_depth — does not follow links beyond configured depth."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_depth_zero_no_link_discovery(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
    ):
        """max_depth=0 crawls seed pages but never calls discover_links."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=0,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 1
        mock_discover.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_depth_one_follows_seed_links(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
    ):
        """max_depth=1 discovers links from seed (depth 0), crawls them."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        mock_discover.return_value = ["https://example.com/child"]
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=1,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 2
        # discover_links called for seed (depth 0 < max_depth 1), not child (depth 1)
        assert mock_discover.call_count == 1

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_does_not_follow_beyond_max_depth(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
    ):
        """With max_depth=2, discover_links called for depth 0 and 1, not 2."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        mock_discover.side_effect = [
            ["https://example.com/child"],  # seed at depth 0
            ["https://example.com/grandchild"],  # child at depth 1
        ]
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=2,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 3
        # discover_links called for depth 0 and 1, NOT depth 2
        assert mock_discover.call_count == 2


# ---------------------------------------------------------------------------
# Max pages
# ---------------------------------------------------------------------------


class TestMaxPages:
    """Respects max_pages — stops crawling after limit."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_stops_after_max_pages(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        mock_discover.return_value = [
            "https://example.com/p2",
            "https://example.com/p3",
            "https://example.com/p4",
        ]
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=1,
            max_pages=2,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 2
        assert len(result.pages) == 2


# ---------------------------------------------------------------------------
# Same-domain filtering
# ---------------------------------------------------------------------------


class TestSameDomainOnly:
    """same_domain_only filters cross-domain links via discover_links."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_passes_config_to_discover_links(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
    ):
        """WebCrawler forwards the CrawlConfig to discover_links for filtering."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        mock_discover.return_value = []
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=1,
            same_domain_only=True,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        await crawler.crawl(config)
        mock_discover.assert_called_once()
        call_args = mock_discover.call_args
        assert call_args[0][2] is config

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_cross_domain_filtered_by_discover_links(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
    ):
        """discover_links only returns same-domain URLs when configured."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        # Simulate discover_links already filtering — returns only same-domain
        mock_discover.return_value = ["https://example.com/internal"]
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=1,
            same_domain_only=True,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 2
        assert all("example.com" in p.url for p in result.pages)


# ---------------------------------------------------------------------------
# Robots.txt compliance
# ---------------------------------------------------------------------------


class TestRobotsTxt:
    """Checks robots.txt before each fetch when respect_robots=True."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    @patch(f"{_MODULE}.RobotsTxtChecker")
    async def test_checks_robots_when_enabled(
        self,
        mock_checker_cls,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        checker = MagicMock()
        checker.load = AsyncMock()
        checker.can_fetch.return_value = True
        mock_checker_cls.return_value = checker

        config = CrawlConfig(seed_urls=_SEED, respect_robots=True, delay_seconds=0)
        crawler = WebCrawler(mock_browser_manager)
        await crawler.crawl(config)

        checker.load.assert_awaited_once()
        checker.can_fetch.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    @patch(f"{_MODULE}.RobotsTxtChecker")
    async def test_skips_page_when_robots_disallows(
        self,
        mock_checker_cls,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        checker = MagicMock()
        checker.load = AsyncMock()
        checker.can_fetch.return_value = False
        mock_checker_cls.return_value = checker

        config = CrawlConfig(seed_urls=_SEED, respect_robots=True, delay_seconds=0)
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)

        assert result.total_pages == 0
        mock_extract.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.RobotsTxtChecker")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_no_robots_check_when_disabled(
        self,
        mock_extract,
        _mock_discover,
        mock_checker_cls,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(seed_urls=_SEED, respect_robots=False, delay_seconds=0)
        crawler = WebCrawler(mock_browser_manager)
        await crawler.crawl(config)
        mock_checker_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Rate limiting: pauses delay_seconds between requests (mock asyncio.sleep)."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_sleeps_between_requests(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(
            seed_urls=["https://example.com", "https://example.com/about"],
            delay_seconds=2.0,
            respect_robots=False,
            same_domain_only=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await crawler.crawl(config)
            # Sleep once between the two requests (not before first)
            mock_sleep.assert_awaited_once_with(2.0)

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_no_sleep_when_delay_zero(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
    ):
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(
            seed_urls=["https://example.com", "https://example.com/about"],
            delay_seconds=0.0,
            respect_robots=False,
            same_domain_only=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await crawler.crawl(config)
            mock_sleep.assert_not_awaited()


# ---------------------------------------------------------------------------
# URL dedup
# ---------------------------------------------------------------------------


class TestUrlDedup:
    """URL dedup: does not visit same normalized URL twice."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_duplicate_seed_urls_visited_once(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
        mock_page,
    ):
        """Identical seed URLs are deduplicated before crawling."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(
            seed_urls=["https://example.com", "https://example.com"],
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 1
        mock_page.goto.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links")
    @patch(f"{_MODULE}.extract_content")
    async def test_discovered_url_not_revisited(
        self,
        mock_extract,
        mock_discover,
        mock_browser_manager,
        mock_page,
    ):
        """A discovered link matching an already-visited URL is skipped."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        # discover_links returns the seed URL again — should be skipped
        mock_discover.return_value = ["https://example.com"]
        config = CrawlConfig(
            seed_urls=_SEED,
            max_depth=1,
            delay_seconds=0,
            respect_robots=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 1
        mock_page.goto.assert_awaited_once()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Page errors are captured in CrawlResult.errors; crawl continues."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_navigation_error_added_to_errors(
        self,
        _mock_extract,
        _mock_discover,
        mock_browser_manager,
        mock_page,
    ):
        mock_page.goto.side_effect = Exception("Navigation failed")
        config = CrawlConfig(seed_urls=_SEED, delay_seconds=0, respect_robots=False)
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 0
        assert len(result.errors) == 1
        assert "Navigation failed" in result.errors[0]

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_MODULE}.discover_links", return_value=[])
    @patch(f"{_MODULE}.extract_content")
    async def test_continues_crawling_after_error(
        self,
        mock_extract,
        _mock_discover,
        mock_browser_manager,
        mock_page,
    ):
        """If one page fails, the crawler continues to the next."""
        mock_page.goto.side_effect = [Exception("fail"), None]
        mock_extract.return_value = _DEFAULT_EXTRACTION
        config = CrawlConfig(
            seed_urls=["https://example.com/bad", "https://example.com/good"],
            delay_seconds=0,
            respect_robots=False,
            same_domain_only=False,
        )
        crawler = WebCrawler(mock_browser_manager)
        result = await crawler.crawl(config)
        assert result.total_pages == 1
        assert len(result.errors) == 1
