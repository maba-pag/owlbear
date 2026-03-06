"""URL utilities — normalize, discover links, robots.txt checker.

Provides :func:`normalize_url` for URL canonicalization,
:func:`discover_links` for extracting and filtering links from HTML,
and :class:`RobotsTxtChecker` for robots.txt compliance checking.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)
from urllib.robotparser import RobotFileParser

import httpx

if TYPE_CHECKING:
    from owlbear.tools.browser.crawl_config import CrawlConfig

# Schemes we should skip when discovering links
_SKIP_SCHEMES = frozenset({"javascript", "mailto", "tel", "data"})


def normalize_url(url: str) -> str:
    """Normalize a URL: lowercase scheme+host, strip trailing slash/fragment, sort query params.

    Args:
        url: The URL string to normalize.

    Returns:
        The normalized URL string.  Returns ``""`` for empty input.
        Relative URLs (no scheme) are returned with trailing slash stripped.
    """
    if not url:
        return ""

    parsed = urlparse(url)

    # No scheme → relative URL, just clean trailing slash
    if not parsed.scheme:
        return url.rstrip("/") or url

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    # Sort query params, drop empty query string
    query_dict = parse_qs(parsed.query, keep_blank_values=True)
    sorted_query = urlencode(
        sorted((k, v[0] if len(v) == 1 else v) for k, v in query_dict.items()),
        doseq=True,
    )

    # Rebuild without fragment
    return urlunparse((scheme, netloc, path, parsed.params, sorted_query, ""))


class _LinkExtractor(HTMLParser):
    """Simple HTML parser that extracts href attributes from <a> tags."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect href values from anchor tags."""
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


def discover_links(html: str, base_url: str, config: CrawlConfig) -> list[str]:
    """Extract, resolve, filter, and normalize links from HTML content.

    Args:
        html: Raw HTML string to parse.
        base_url: The URL the HTML was fetched from (for resolving relative links).
        config: Crawl configuration controlling domain/pattern filtering.

    Returns:
        Deduplicated list of normalized URLs that pass all filters.
    """
    # Extract raw hrefs
    parser = _LinkExtractor()
    parser.feed(html)

    base_parsed = urlparse(base_url)
    seen: set[str] = set()
    result: list[str] = []

    # Precompile patterns
    allow_re = [re.compile(p) for p in config.allow_patterns]
    deny_re = [re.compile(p) for p in config.deny_patterns]

    for raw_href in parser.links:
        # Resolve relative URLs
        absolute = urljoin(base_url, raw_href)
        abs_parsed = urlparse(absolute)

        # Skip non-HTTP schemes
        if abs_parsed.scheme in _SKIP_SCHEMES:
            continue

        # Normalize
        normalized = normalize_url(absolute)
        if not normalized:
            continue

        # Deduplicate
        if normalized in seen:
            continue

        # Same-domain filter
        if config.same_domain_only:
            norm_parsed = urlparse(normalized)
            if norm_parsed.netloc != base_parsed.netloc.lower():
                continue

        # Allow-patterns filter (whitelist — if set, URL must match at least one)
        if allow_re and not any(r.search(normalized) for r in allow_re):
            continue

        # Deny-patterns filter (blacklist — if any match, skip)
        if any(r.search(normalized) for r in deny_re):
            continue

        seen.add(normalized)
        result.append(normalized)

    return result


class RobotsTxtChecker:
    """Async-friendly robots.txt compliance checker.

    Wraps :class:`urllib.robotparser.RobotFileParser` with async loading
    via httpx. Handles missing or unreachable robots.txt gracefully by
    defaulting to allow-all.

    Args:
        user_agent: The User-Agent string to check rules against.
    """

    def __init__(self, user_agent: str) -> None:
        self._user_agent = user_agent
        self._parser: RobotFileParser | None = None
        self._loaded = False

    async def load(self, url: str) -> None:
        """Fetch and parse robots.txt for the given URL's domain.

        On any failure (404, connection error, timeout), defaults to
        allow-all by leaving the parser unset.

        Args:
            url: Any URL on the target domain; robots.txt is derived from its origin.
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10, connect=5),
            ) as client:
                response = await client.get(robots_url, follow_redirects=True)

            if response.status_code == 200:  # noqa: PLR2004
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                self._parser = parser
        except (httpx.HTTPError, OSError):
            # Connection errors, timeouts, etc. → default allow
            pass

        self._loaded = True

    def can_fetch(self, url: str) -> bool:
        """Check whether the URL is allowed by robots.txt rules.

        Returns:
            ``True`` if the URL is allowed or robots.txt was unavailable.
        """
        if self._parser is None:
            return True
        return self._parser.can_fetch(self._user_agent, url)

    def crawl_delay(self) -> float | None:
        """Return the Crawl-delay directive value, or ``None`` if absent.

        Returns:
            The delay in seconds as a float, or ``None``.
        """
        if self._parser is None:
            return None
        delay = self._parser.crawl_delay(self._user_agent)
        if delay is None:
            return None
        return float(delay)
