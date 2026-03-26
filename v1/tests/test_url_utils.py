"""Tests for URL utilities — normalize, discover links, robots.txt checker."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from owlbear.tools.browser.crawl_config import CrawlConfig
from owlbear.tools.browser.url_utils import (
    RobotsTxtChecker,
    discover_links,
    normalize_url,
)

_SEED = ["https://example.com"]


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    """normalize_url lowercases scheme+host, strips trailing slash/fragment, sorts query."""

    def test_lowercase_scheme_and_host(self) -> None:
        assert normalize_url("HTTPS://Example.COM/path") == "https://example.com/path"

    def test_strips_trailing_slash(self) -> None:
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_strips_fragment(self) -> None:
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_sorts_query_params(self) -> None:
        result = normalize_url("https://example.com/page?z=1&a=2&m=3")
        assert result == "https://example.com/page?a=2&m=3&z=1"

    def test_combined_normalization(self) -> None:
        url = "HTTPS://Example.COM/path/?z=1&a=2#frag"
        result = normalize_url(url)
        assert result == "https://example.com/path?a=2&z=1"

    def test_preserves_path_case(self) -> None:
        assert normalize_url("https://example.com/CamelCase") == "https://example.com/CamelCase"

    def test_preserves_query_value_case(self) -> None:
        result = normalize_url("https://example.com/p?key=VaLuE")
        assert result == "https://example.com/p?key=VaLuE"

    def test_no_query_no_fragment(self) -> None:
        assert normalize_url("https://example.com/page") == "https://example.com/page"

    def test_empty_query_string(self) -> None:
        # A URL with "?" but no params — strip the "?"
        result = normalize_url("https://example.com/page?")
        assert result == "https://example.com/page"


class TestNormalizeUrlEdgeCases:
    """Edge cases: empty string, relative URLs, non-HTTP schemes."""

    def test_empty_string_returns_empty(self) -> None:
        assert normalize_url("") == ""

    def test_relative_url_returned_as_is(self) -> None:
        # Without a scheme, we cannot normalise host — return cleaned path
        assert normalize_url("/relative/path") == "/relative/path"

    def test_non_http_scheme_passthrough(self) -> None:
        # FTP, mailto, etc. — still lowercase scheme+host
        result = normalize_url("FTP://Files.Example.COM/pub/")
        assert result == "ftp://files.example.com/pub"

    def test_mailto_scheme(self) -> None:
        # mailto: has no netloc — domain stays in path, only scheme is lowercased
        result = normalize_url("mailto:user@Example.COM")
        assert result == "mailto:user@Example.COM"

    def test_url_with_port(self) -> None:
        result = normalize_url("https://Example.COM:8080/path/")
        assert result == "https://example.com:8080/path"

    def test_url_with_userinfo(self) -> None:
        result = normalize_url("https://user:pass@Example.COM/path")
        assert result == "https://user:pass@example.com/path"


# ---------------------------------------------------------------------------
# discover_links
# ---------------------------------------------------------------------------


_BASE = "https://example.com/page"


class TestDiscoverLinks:
    """discover_links extracts <a href> links, resolves relative, filters, normalizes."""

    def test_extracts_absolute_links(self) -> None:
        html = '<a href="https://example.com/about">About</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert "https://example.com/about" in links

    def test_resolves_relative_urls(self) -> None:
        html = '<a href="/docs/intro">Intro</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert "https://example.com/docs/intro" in links

    def test_resolves_relative_without_leading_slash(self) -> None:
        html = '<a href="sub/page">Sub</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, "https://example.com/dir/", cfg)
        assert "https://example.com/dir/sub/page" in links

    def test_multiple_links(self) -> None:
        html = """
        <a href="/one">One</a>
        <a href="/two">Two</a>
        <a href="/three">Three</a>
        """
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert len(links) == 3

    def test_deduplicates_links(self) -> None:
        html = """
        <a href="/page">Page</a>
        <a href="/page#section">Page with fragment</a>
        """
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        # Both normalize to the same URL
        assert len(links) == 1

    def test_skips_empty_href(self) -> None:
        html = '<a href="">Empty</a><a>No href</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert links == []

    def test_skips_javascript_href(self) -> None:
        html = '<a href="javascript:void(0)">JS</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert links == []

    def test_skips_mailto_href(self) -> None:
        html = '<a href="mailto:user@example.com">Mail</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert links == []


class TestDiscoverLinksFiltering:
    """discover_links filters by same_domain, allow_patterns, deny_patterns."""

    def test_same_domain_filters_external(self) -> None:
        html = """
        <a href="https://example.com/internal">Internal</a>
        <a href="https://other.com/external">External</a>
        """
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=True)
        links = discover_links(html, _BASE, cfg)
        assert "https://example.com/internal" in links
        assert not any("other.com" in u for u in links)

    def test_same_domain_disabled_allows_external(self) -> None:
        html = """
        <a href="https://example.com/internal">Internal</a>
        <a href="https://other.com/external">External</a>
        """
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert len(links) == 2

    def test_allow_patterns_whitelist(self) -> None:
        html = """
        <a href="/docs/page">Docs</a>
        <a href="/blog/post">Blog</a>
        """
        cfg = CrawlConfig(
            seed_urls=_SEED,
            same_domain_only=False,
            allow_patterns=[r"/docs/"],
        )
        links = discover_links(html, _BASE, cfg)
        assert len(links) == 1
        assert "docs" in links[0]

    def test_deny_patterns_blacklist(self) -> None:
        html = """
        <a href="/docs/page">Docs</a>
        <a href="/login">Login</a>
        """
        cfg = CrawlConfig(
            seed_urls=_SEED,
            same_domain_only=False,
            deny_patterns=[r"/login"],
        )
        links = discover_links(html, _BASE, cfg)
        assert len(links) == 1
        assert "docs" in links[0]

    def test_deny_overrides_allow(self) -> None:
        html = '<a href="/docs/secret">Secret</a>'
        cfg = CrawlConfig(
            seed_urls=_SEED,
            same_domain_only=False,
            allow_patterns=[r"/docs/"],
            deny_patterns=[r"secret"],
        )
        links = discover_links(html, _BASE, cfg)
        assert links == []


class TestDiscoverLinksNormalized:
    """discover_links returns normalized URLs."""

    def test_returned_urls_are_normalized(self) -> None:
        html = '<a href="https://Example.COM/Path/?z=1&a=2#frag">Link</a>'
        cfg = CrawlConfig(seed_urls=_SEED, same_domain_only=False)
        links = discover_links(html, _BASE, cfg)
        assert links == ["https://example.com/Path?a=2&z=1"]


# ---------------------------------------------------------------------------
# RobotsTxtChecker
# ---------------------------------------------------------------------------


class TestRobotsTxtCheckerCanFetch:
    """RobotsTxtChecker.can_fetch returns True/False per robots.txt rules."""

    @pytest.mark.anyio
    async def test_disallowed_url(self) -> None:
        robots_content = "User-agent: *\nDisallow: /private/\n"
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = httpx.Response(
                200,
                text=robots_content,
                request=httpx.Request("GET", "https://example.com/robots.txt"),
            )
            await checker.load("https://example.com/private/page")

        assert checker.can_fetch("https://example.com/private/page") is False

    @pytest.mark.anyio
    async def test_allowed_url(self) -> None:
        robots_content = "User-agent: *\nDisallow: /private/\n"
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = httpx.Response(
                200,
                text=robots_content,
                request=httpx.Request("GET", "https://example.com/robots.txt"),
            )
            await checker.load("https://example.com/public/page")

        assert checker.can_fetch("https://example.com/public/page") is True

    @pytest.mark.anyio
    async def test_specific_user_agent_rule(self) -> None:
        robots_content = "User-agent: OwlBear\nDisallow: /restricted/\n\nUser-agent: *\nAllow: /\n"
        checker = RobotsTxtChecker(user_agent="OwlBear")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = httpx.Response(
                200,
                text=robots_content,
                request=httpx.Request("GET", "https://example.com/robots.txt"),
            )
            await checker.load("https://example.com/restricted/page")

        assert checker.can_fetch("https://example.com/restricted/page") is False


class TestRobotsTxtCheckerCrawlDelay:
    """RobotsTxtChecker.crawl_delay returns delay value or None."""

    @pytest.mark.anyio
    async def test_crawl_delay_present(self) -> None:
        robots_content = "User-agent: *\nCrawl-delay: 5\n"
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = httpx.Response(
                200,
                text=robots_content,
                request=httpx.Request("GET", "https://example.com/robots.txt"),
            )
            await checker.load("https://example.com/")

        assert checker.crawl_delay() == 5.0

    @pytest.mark.anyio
    async def test_crawl_delay_absent(self) -> None:
        robots_content = "User-agent: *\nDisallow: /private/\n"
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = httpx.Response(
                200,
                text=robots_content,
                request=httpx.Request("GET", "https://example.com/robots.txt"),
            )
            await checker.load("https://example.com/")

        assert checker.crawl_delay() is None


class TestRobotsTxtCheckerGracefulFailure:
    """RobotsTxtChecker handles missing/unreachable robots.txt (default allow)."""

    @pytest.mark.anyio
    async def test_404_defaults_to_allow(self) -> None:
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = httpx.Response(
                404,
                request=httpx.Request("GET", "https://example.com/robots.txt"),
            )
            await checker.load("https://example.com/any/page")

        assert checker.can_fetch("https://example.com/any/page") is True

    @pytest.mark.anyio
    async def test_connection_error_defaults_to_allow(self) -> None:
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            await checker.load("https://unreachable.com/page")

        assert checker.can_fetch("https://unreachable.com/page") is True

    @pytest.mark.anyio
    async def test_connection_error_crawl_delay_is_none(self) -> None:
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            await checker.load("https://unreachable.com/")

        assert checker.crawl_delay() is None

    @pytest.mark.anyio
    async def test_timeout_defaults_to_allow(self) -> None:
        checker = RobotsTxtChecker(user_agent="OwlBear/1.0")
        with patch("owlbear.tools.browser.url_utils.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = httpx.TimeoutException("Timed out")
            await checker.load("https://slow.com/page")

        assert checker.can_fetch("https://slow.com/page") is True
