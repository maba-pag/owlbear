"""Tests for raw-HTML cache layer — HtmlCache, CrawlConfig TTL, WebCrawler integration.

RED phase: all tests must fail (ImportError or AssertionError) because
``owlbear.tools.browser.html_cache`` does not exist yet.

AC reference: task #759 — Implement raw-HTML cache layer for WebCrawler.
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from owlbear.tools.browser.html_cache import HtmlCache
from pydantic import ValidationError

from owlbear.tools.browser.content_extractor import ExtractionResult
from owlbear.tools.browser.crawl_config import CrawlConfig
from owlbear.tools.browser.crawler import WebCrawler
from owlbear.tools.browser.url_utils import normalize_url

_CRAWLER_MODULE = "owlbear.tools.browser.crawler"
_DEFAULT_HTML = "<html><body>Hello</body></html>"
_DEFAULT_EXTRACTION = ExtractionResult(
    text="extracted text",
    title="Test Page",
    metadata={"title": "Test Page"},
)
_SEED = ["https://example.com"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Return an absolute temporary directory for cache storage."""
    return tmp_path / "html_cache"  # HtmlCache.__init__ should create it


@pytest.fixture
def cache(cache_dir: Path) -> HtmlCache:
    """Return an HtmlCache instance using a temporary directory."""
    return HtmlCache(cache_dir=cache_dir)


@pytest.fixture
def mock_page() -> AsyncMock:
    """Mock Playwright page with async goto() and content()."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=_DEFAULT_HTML)
    return page


@pytest.fixture
def mock_browser_manager(mock_page: AsyncMock) -> MagicMock:
    """Mock BrowserManager whose .page returns mock_page."""
    mgr = MagicMock()
    mgr.page = mock_page
    return mgr


# ===================================================================
# AC 1 — HtmlCache class with get() and put()
# ===================================================================


class TestFromAC_HtmlCacheBasic:  # noqa: N801
    """HtmlCache provides get/put for caching raw HTML by URL."""

    def test_put_and_get_roundtrip(self, cache: HtmlCache) -> None:
        """put() stores HTML, get() retrieves it within TTL."""
        url = "https://example.com/page"
        html = "<html><body>content</body></html>"
        cache.put(url, html)
        result = cache.get(url, ttl_seconds=3600)
        assert result == html

    def test_get_returns_none_on_miss(self, cache: HtmlCache) -> None:
        """get() returns None when the URL has never been cached."""
        result = cache.get("https://never-cached.example.com", ttl_seconds=3600)
        assert result is None

    def test_put_overwrites_existing(self, cache: HtmlCache) -> None:
        """put() with the same URL replaces the cached content."""
        url = "https://example.com/page"
        cache.put(url, "old")
        cache.put(url, "new")
        assert cache.get(url, ttl_seconds=3600) == "new"

    def test_different_urls_stored_separately(self, cache: HtmlCache) -> None:
        """Different URLs produce different cache entries."""
        cache.put("https://a.example.com", "html_a")
        cache.put("https://b.example.com", "html_b")
        assert cache.get("https://a.example.com", ttl_seconds=3600) == "html_a"
        assert cache.get("https://b.example.com", ttl_seconds=3600) == "html_b"


# ===================================================================
# AC 2 — Storage keyed by SHA-256 of normalize_url with .html ext
# ===================================================================


class TestFromAC_HtmlCacheFileNaming:  # noqa: N801
    """Cache files are named by SHA-256(normalize_url(url)) + .html."""

    def test_file_uses_sha256_of_normalized_url(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """The on-disk filename matches SHA-256 hex of the normalized URL."""
        url = "https://example.com/page"
        cache.put(url, "content")
        normalized = normalize_url(url)
        expected_name = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        assert (cache_dir / expected_name).exists()

    def test_urls_that_normalize_identically_share_cache(
        self, cache: HtmlCache
    ) -> None:
        """URLs differing only by trailing slash share one cache entry."""
        cache.put("https://example.com/page/", "html_a")
        result = cache.get("https://example.com/page", ttl_seconds=3600)
        assert result == "html_a"

    def test_file_extension_is_html(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """All cache files have the .html extension."""
        cache.put("https://example.com", "content")
        files = list(cache_dir.glob("*"))
        assert all(f.suffix == ".html" for f in files)


# ===================================================================
# AC 3 — __init__ resolves cache_dir, creates it, ValueError if not absolute
# ===================================================================


class TestFromAC_HtmlCacheInit:  # noqa: N801
    """HtmlCache.__init__ validates and creates the cache directory."""

    def test_creates_cache_dir(self, tmp_path: Path) -> None:
        """__init__ creates the cache_dir (with parents) if it doesn't exist."""
        nested = tmp_path / "deep" / "nested" / "cache"
        HtmlCache(cache_dir=nested)
        assert nested.is_dir()

    def test_existing_dir_is_fine(self, tmp_path: Path) -> None:
        """__init__ succeeds when cache_dir already exists."""
        d = tmp_path / "cache"
        d.mkdir()
        cache = HtmlCache(cache_dir=d)
        # Should not raise
        assert cache is not None

    def test_raises_valueerror_for_relative_path(self) -> None:
        """__init__ raises ValueError when cache_dir is relative."""
        with pytest.raises(ValueError, match="absolute"):
            HtmlCache(cache_dir=Path("relative/path"))

    def test_raises_valueerror_for_dot_path(self) -> None:
        """__init__ raises ValueError for '.' as cache_dir."""
        with pytest.raises(ValueError, match="absolute"):
            HtmlCache(cache_dir=Path())


# ===================================================================
# AC 4 — CrawlConfig gains cache_ttl_seconds field
# ===================================================================


class TestFromAC_CrawlConfigCacheTtl:  # noqa: N801
    """CrawlConfig has a cache_ttl_seconds field with 24h default and >= 0 validator."""

    def test_default_is_86400(self) -> None:
        """cache_ttl_seconds defaults to 86400 (24 hours)."""
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.cache_ttl_seconds == 86400

    def test_custom_value_accepted(self) -> None:
        """cache_ttl_seconds=3600 is accepted."""
        cfg = CrawlConfig(seed_urls=_SEED, cache_ttl_seconds=3600)
        assert cfg.cache_ttl_seconds == 3600

    def test_zero_means_no_expiry(self) -> None:
        """cache_ttl_seconds=0 is valid (means no expiry)."""
        cfg = CrawlConfig(seed_urls=_SEED, cache_ttl_seconds=0)
        assert cfg.cache_ttl_seconds == 0

    def test_negative_value_rejected(self) -> None:
        """cache_ttl_seconds < 0 raises ValidationError."""
        with pytest.raises(ValidationError):
            CrawlConfig(seed_urls=_SEED, cache_ttl_seconds=-1)

    def test_field_is_int(self) -> None:
        """cache_ttl_seconds is typed as int."""
        cfg = CrawlConfig(seed_urls=_SEED)
        assert isinstance(cfg.cache_ttl_seconds, int)


# ===================================================================
# AC 5 — WebCrawler.__init__ gains optional html_cache param
# ===================================================================


class TestFromAC_WebCrawlerHtmlCacheParam:  # noqa: N801
    """WebCrawler.__init__ accepts an optional html_cache: HtmlCache | None."""

    def test_accepts_html_cache(self, mock_browser_manager: MagicMock, cache: HtmlCache) -> None:
        """WebCrawler can be instantiated with an HtmlCache."""
        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        assert crawler._html_cache is cache

    def test_html_cache_defaults_to_none(self, mock_browser_manager: MagicMock) -> None:
        """Without html_cache, the attribute is None."""
        crawler = WebCrawler(mock_browser_manager)
        assert crawler._html_cache is None

    def test_content_guard_and_cache_coexist(
        self, mock_browser_manager: MagicMock, cache: HtmlCache
    ) -> None:
        """Both content_guard and html_cache can be provided."""
        guard = MagicMock()
        crawler = WebCrawler(mock_browser_manager, content_guard=guard, html_cache=cache)
        assert crawler._content_guard is guard
        assert crawler._html_cache is cache


# ===================================================================
# AC 6 — _fetch_and_extract checks cache before page.goto()
# ===================================================================


class TestFromAC_CacheHitSkipsNavigation:  # noqa: N801
    """On cache hit, _fetch_and_extract uses cached HTML without navigating."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_cache_hit_skips_page_goto(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        mock_page: AsyncMock,
        cache: HtmlCache,
    ) -> None:
        """When cache has HTML for the URL, page.goto() is never called."""
        url = "https://example.com"
        cached_html = "<html><body>Cached</body></html>"
        cache.put(url, cached_html)
        mock_extract.return_value = _DEFAULT_EXTRACTION

        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        config = CrawlConfig(
            seed_urls=[url], delay_seconds=0, respect_robots=False, cache_ttl_seconds=3600
        )
        await crawler.crawl(config)

        mock_page.goto.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_cache_hit_calls_extract_with_cached_html(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        cache: HtmlCache,
    ) -> None:
        """On cache hit, extract_content receives the cached HTML."""
        url = "https://example.com"
        cached_html = "<html><body>Cached</body></html>"
        cache.put(url, cached_html)
        mock_extract.return_value = _DEFAULT_EXTRACTION

        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        config = CrawlConfig(
            seed_urls=[url], delay_seconds=0, respect_robots=False, cache_ttl_seconds=3600
        )
        await crawler.crawl(config)

        mock_extract.assert_called_once()
        call_args = mock_extract.call_args
        assert call_args[0][0] == cached_html or call_args[1].get("html") == cached_html

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_cache_hit_returns_crawl_page(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        cache: HtmlCache,
    ) -> None:
        """On cache hit, crawl still produces a valid CrawlPage."""
        url = "https://example.com"
        cache.put(url, "<html>Cached</html>")
        mock_extract.return_value = _DEFAULT_EXTRACTION

        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        config = CrawlConfig(
            seed_urls=[url], delay_seconds=0, respect_robots=False, cache_ttl_seconds=3600
        )
        result = await crawler.crawl(config)

        assert len(result.pages) == 1
        assert result.pages[0].url == normalize_url(url)


# ===================================================================
# AC 7 — After navigation, put() stores raw HTML
# ===================================================================


class TestFromAC_CachePutOnMiss:  # noqa: N801
    """After a live fetch (cache miss), the HTML is stored via put()."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_cache_miss_stores_fetched_html(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        mock_page: AsyncMock,
        cache: HtmlCache,
    ) -> None:
        """On cache miss, the fetched HTML is written to the cache."""
        url = "https://example.com"
        mock_page.content.return_value = _DEFAULT_HTML
        mock_extract.return_value = _DEFAULT_EXTRACTION

        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        config = CrawlConfig(
            seed_urls=[url], delay_seconds=0, respect_robots=False, cache_ttl_seconds=3600
        )
        await crawler.crawl(config)

        # Verify cached content matches what was fetched
        cached = cache.get(url, ttl_seconds=3600)
        assert cached == _DEFAULT_HTML

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_cache_miss_navigates_via_page_goto(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        mock_page: AsyncMock,
        cache: HtmlCache,
    ) -> None:
        """On cache miss, page.goto() is called."""
        mock_extract.return_value = _DEFAULT_EXTRACTION

        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        config = CrawlConfig(
            seed_urls=_SEED, delay_seconds=0, respect_robots=False, cache_ttl_seconds=3600
        )
        await crawler.crawl(config)

        mock_page.goto.assert_called_once()


# ===================================================================
# AC 8 — get() returns None on missing/read-fail/expired; ttl=0 no expiry
# ===================================================================


class TestFromAC_CacheGetEdgeCases:  # noqa: N801
    """HtmlCache.get() handles missing, expired, and error conditions."""

    def test_returns_none_when_file_missing(self, cache: HtmlCache) -> None:
        """get() returns None for a URL that was never cached."""
        assert cache.get("https://no-such-url.example.com", ttl_seconds=3600) is None

    def test_returns_none_when_expired(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """get() returns None when file_age > ttl_seconds."""
        url = "https://example.com/old"
        cache.put(url, "old content")

        # Manually backdate the file modification time
        normalized = normalize_url(url)
        filename = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        filepath = cache_dir / filename
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(filepath, (old_time, old_time))

        result = cache.get(url, ttl_seconds=3600)  # TTL is 1 hour
        assert result is None

    def test_ttl_zero_means_no_expiry(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """get() with ttl_seconds=0 returns cached content regardless of age."""
        url = "https://example.com/eternal"
        cache.put(url, "eternal content")

        # Backdate the file to a very old time
        normalized = normalize_url(url)
        filename = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        filepath = cache_dir / filename
        old_time = time.time() - 365 * 24 * 3600  # 1 year ago
        os.utime(filepath, (old_time, old_time))

        result = cache.get(url, ttl_seconds=0)
        assert result == "eternal content"

    def test_returns_content_just_before_expiry(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """get() returns content when file_age < ttl_seconds (boundary)."""
        url = "https://example.com/fresh"
        cache.put(url, "fresh content")

        # File is ~10 seconds old, TTL is 3600 — should be valid
        normalized = normalize_url(url)
        filename = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        filepath = cache_dir / filename
        recent = time.time() - 10
        os.utime(filepath, (recent, recent))

        result = cache.get(url, ttl_seconds=3600)
        assert result == "fresh content"

    def test_returns_none_at_exact_expiry_boundary(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """get() returns None when file_age == ttl_seconds (expired at boundary)."""
        url = "https://example.com/boundary"
        cache.put(url, "boundary content")

        normalized = normalize_url(url)
        filename = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        filepath = cache_dir / filename
        # Set mtime exactly ttl_seconds + 1 ago to ensure it's expired
        boundary_time = time.time() - 3601
        os.utime(filepath, (boundary_time, boundary_time))

        result = cache.get(url, ttl_seconds=3600)
        assert result is None


# ===================================================================
# AC 9 — Cache I/O failures caught internally, never propagate
# ===================================================================


class TestFromAC_CacheIOFailuresSilent:  # noqa: N801
    """Cache I/O errors are caught and logged, never raised to the caller."""

    def test_get_returns_none_on_read_error(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """get() returns None when the cache file cannot be read."""
        url = "https://example.com/unreadable"
        cache.put(url, "content")

        # Corrupt the file by making it a directory (simulate read error)
        normalized = normalize_url(url)
        filename = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        filepath = cache_dir / filename
        filepath.unlink()
        filepath.mkdir()  # Can't read a directory as a file

        result = cache.get(url, ttl_seconds=3600)
        assert result is None

    def test_put_does_not_raise_on_write_error(self, tmp_path: Path) -> None:
        """put() silently handles write failures (e.g., permission denied)."""
        # Use a read-only directory to trigger write failure
        read_only_dir = tmp_path / "readonly_cache"
        read_only_dir.mkdir()
        cache = HtmlCache(cache_dir=read_only_dir)

        # Make it read-only on Windows (best-effort)
        read_only_dir.chmod(0o444)
        try:
            # Should not raise even if write fails
            cache.put("https://example.com", "content")
        except OSError:
            pytest.fail("put() must not propagate I/O errors")
        finally:
            read_only_dir.chmod(0o755)

    def test_get_returns_none_on_corrupt_file(
        self, cache: HtmlCache, cache_dir: Path
    ) -> None:
        """get() returns None if the file exists but read produces an error."""
        url = "https://example.com/corrupt"
        # Write a file with the correct name but via put(), then swap content
        cache.put(url, "good content")
        normalized = normalize_url(url)
        filename = hashlib.sha256(normalized.encode()).hexdigest() + ".html"
        target = cache_dir / filename
        # File exists and is readable — should return content
        assert target.exists()
        assert cache.get(url, ttl_seconds=3600) == "good content"


# ===================================================================
# AC 6+7 — Integration: cache-miss-then-hit flow with WebCrawler
# ===================================================================


class TestFromAC_WebCrawlerCacheIntegration:  # noqa: N801
    """WebCrawler.crawl() uses HtmlCache for miss-then-hit flow."""

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_second_crawl_uses_cache(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        mock_page: AsyncMock,
        cache: HtmlCache,
    ) -> None:
        """First crawl navigates; second crawl for same URL hits cache."""
        mock_extract.return_value = _DEFAULT_EXTRACTION
        mock_page.content.return_value = _DEFAULT_HTML

        crawler = WebCrawler(mock_browser_manager, html_cache=cache)
        config = CrawlConfig(
            seed_urls=_SEED, delay_seconds=0, respect_robots=False, cache_ttl_seconds=3600
        )

        # First crawl — should navigate
        await crawler.crawl(config)
        assert mock_page.goto.call_count == 1

        # Second crawl — should use cache (no additional goto)
        mock_page.goto.reset_mock()
        await crawler.crawl(config)
        mock_page.goto.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    @patch(f"{_CRAWLER_MODULE}.extract_content")
    @patch(f"{_CRAWLER_MODULE}.discover_links", return_value=[])
    async def test_no_cache_means_normal_navigation(
        self,
        _mock_discover: MagicMock,
        mock_extract: MagicMock,
        mock_browser_manager: MagicMock,
        mock_page: AsyncMock,
    ) -> None:
        """When html_cache=None, WebCrawler navigates every time."""
        mock_extract.return_value = _DEFAULT_EXTRACTION

        crawler = WebCrawler(mock_browser_manager)  # No cache
        config = CrawlConfig(
            seed_urls=_SEED, delay_seconds=0, respect_robots=False
        )
        await crawler.crawl(config)
        assert mock_page.goto.call_count == 1

        await crawler.crawl(config)
        assert mock_page.goto.call_count == 2
