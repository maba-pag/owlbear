"""Web crawler — async BFS crawl orchestrator using BrowserManager.

Provides :class:`WebCrawler` with an :meth:`crawl` method that performs
a breadth-first crawl starting from seed URLs, respecting depth/page
limits, robots.txt, and rate limiting.  Uses :func:`extract_content` for
content extraction and :func:`discover_links` for link discovery.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from pydantic import BaseModel

from owlbear.tools.browser.content_extractor import extract_content
from owlbear.tools.browser.url_utils import (
    RobotsTxtChecker,
    discover_links,
    normalize_url,
)

if TYPE_CHECKING:
    from owlbear.tools.browser.content_guard import ContentInjectionGuard
    from owlbear.tools.browser.crawl_config import CrawlConfig
    from owlbear.tools.browser.manager import BrowserManager

logger = logging.getLogger(__name__)


class CrawlPage(BaseModel, frozen=True):
    """A single crawled page.

    Attributes:
        url: The normalized URL of the page.
        content: Extracted text content (Markdown format).
        title: Page title, or ``None`` if unavailable.
        metadata: Additional metadata from content extraction.
    """

    url: str
    content: str
    title: str | None = None
    metadata: dict[str, Any] = {}


class CrawlResult(BaseModel, frozen=True):
    """Result of a crawl operation.

    Attributes:
        pages: List of successfully crawled pages.
        total_pages: Number of pages crawled.
        errors: List of error messages for pages that failed.
    """

    pages: list[CrawlPage]
    total_pages: int
    errors: list[str] = []


class WebCrawler:
    """Async BFS web crawler using BrowserManager for page rendering.

    Navigates pages via Playwright, extracts content with trafilatura,
    discovers links, and respects robots.txt and rate limiting.

    Args:
        browser_manager: The BrowserManager instance for page navigation.
        content_guard: Optional content injection guard for scanning
            extracted text.
    """

    def __init__(
        self,
        browser_manager: BrowserManager,
        content_guard: ContentInjectionGuard | None = None,
    ) -> None:
        self._browser_manager = browser_manager
        self._content_guard = content_guard

    async def crawl(self, config: CrawlConfig) -> CrawlResult:
        """Perform a breadth-first crawl starting from seed URLs.

        Args:
            config: Crawl configuration with seed URLs, depth/page limits,
                and politeness settings.

        Returns:
            A CrawlResult with the list of crawled pages and any errors.
        """
        queue, visited = self._seed_queue(config)
        pages: list[CrawlPage] = []
        errors: list[str] = []
        robots_checkers: dict[str, RobotsTxtChecker] = {}
        first_fetch = True

        while queue and len(pages) < config.max_pages:
            url, depth = queue.popleft()

            if config.respect_robots and not await self._check_robots(
                url,
                config,
                robots_checkers,
            ):
                continue

            if not first_fetch and config.delay_seconds > 0:
                await asyncio.sleep(config.delay_seconds)
            first_fetch = False

            try:
                crawl_page, html = await self._fetch_and_extract(url)
            except Exception as exc:  # noqa: BLE001 — per-page errors are captured
                errors.append(f"{url}: {exc}")
                logger.debug("Page failed for %s: %s", url, exc)
                continue

            if self._content_guard is not None:
                check = self._content_guard.scan(crawl_page.content)
                if check.blocked:
                    errors.append(f"{url}: content injection detected")
                    logger.debug("Content injection blocked for %s", url)
                    continue

            pages.append(crawl_page)

            if depth < config.max_depth:
                for link in discover_links(html, url, config):
                    if link not in visited:
                        visited.add(link)
                        queue.append((link, depth + 1))

        return CrawlResult(
            pages=pages,
            total_pages=len(pages),
            errors=errors,
        )

    # -- private helpers --

    @staticmethod
    def _seed_queue(
        config: CrawlConfig,
    ) -> tuple[deque[tuple[str, int]], set[str]]:
        """Build the initial BFS queue from seed URLs."""
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        for url in config.seed_urls:
            normalized = normalize_url(url)
            if normalized and normalized not in visited:
                queue.append((normalized, 0))
                visited.add(normalized)
        return queue, visited

    async def _check_robots(
        self,
        url: str,
        config: CrawlConfig,
        cache: dict[str, RobotsTxtChecker],
    ) -> bool:
        """Return True if robots.txt allows fetching *url*."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain not in cache:
            checker = RobotsTxtChecker(user_agent=config.user_agent)
            await checker.load(url)
            cache[domain] = checker
        allowed = cache[domain].can_fetch(url)
        if not allowed:
            logger.debug("Robots.txt disallows: %s", url)
        return allowed

    async def _fetch_and_extract(self, url: str) -> tuple[CrawlPage, str]:
        """Navigate to *url*, fetch HTML, extract content.

        Returns:
            A ``(CrawlPage, html)`` tuple.

        Raises:
            Exception: On navigation or extraction failure.
        """
        page = self._browser_manager.page
        await page.goto(url)
        html = await page.content()
        extraction = extract_content(html, url=url)
        return CrawlPage(
            url=url,
            content=extraction.text,
            title=extraction.title,
            metadata=extraction.metadata,
        ), html
