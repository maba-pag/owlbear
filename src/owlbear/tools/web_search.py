"""WebSearchToolset — FunctionToolset wrapping web search and page reading.

Provides ``web_search`` and ``web_read`` — internet search via DuckDuckGo
and page content extraction via httpx + extract_content.

Usage::

    from owlbear.tools.web_search import WebSearchToolset

    toolset = WebSearchToolset(
        blocked_urls=[r".*evil\\.com.*"],
        allowed_urls=[r".*example\\.com.*"],
    )
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

import httpx
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.errors import error_to_user_message
from owlbear.core.retry import TRANSIENT_RETRY
from owlbear.tools.browser.content_extractor import extract_content

if TYPE_CHECKING:
    from typing import ClassVar

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import RatelimitException as _RatelimitException
except ImportError:  # pragma: no cover
    DDGS = None  # type: ignore[assignment,misc]
    _RatelimitException = None  # type: ignore[assignment]

__all__ = ["WebSearchToolset"]

logger = logging.getLogger(__name__)


class WebSearchToolset(FunctionToolset):
    """FunctionToolset subclass exposing 2 web tools: search and read.

    URLs are checked against *blocked_urls* / *allowed_urls* regex
    patterns before being included in results or fetched.

    **Evaluation order** (mirrors :class:`URLSafetyGuard`):

    1. If ``blocked_urls`` contains a matching pattern → **reject**.
    2. If ``allowed_urls`` is non-empty and no pattern matches → **reject**.
    3. Otherwise → **allow**.

    Args:
        blocked_urls: Regex patterns for URLs to reject.
        allowed_urls: Regex patterns for URLs to allow (allowlist mode).
    """

    tool_alias: ClassVar[str] = "web_search"

    def __init__(
        self,
        blocked_urls: list[str] | None = None,
        allowed_urls: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._blocked_urls: list[re.Pattern[str]] = [re.compile(p) for p in (blocked_urls or [])]
        self._allowed_urls: list[re.Pattern[str]] = [re.compile(p) for p in (allowed_urls or [])]
        self._register_tools()

    # ------------------------------------------------------------------
    # URL safety check
    # ------------------------------------------------------------------

    def _check_url(self, url: str) -> None:
        """Check *url* against blocked/allowed patterns.

        Raises:
            ValueError: If the URL is blocked or not in allowlist.
        """
        # 1. Blocklist takes absolute precedence.
        for pat in self._blocked_urls:
            if pat.search(url):
                msg = f"URL blocked by pattern {pat.pattern!r}: {url}"
                logger.debug(msg)
                raise ValueError(msg)

        # 2. If an allowlist exists, URL must match at least one entry.
        if self._allowed_urls:
            for pat in self._allowed_urls:
                if pat.search(url):
                    return
            msg = f"URL not in allowed patterns: {url}"
            logger.debug(msg)
            raise ValueError(msg)

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register web_search and web_read tools on this toolset."""
        self.add_function(
            self._web_search,
            name="web_search",
            description=(
                "Search the web using DuckDuckGo. Returns numbered results "
                "with title, URL, and snippet."
            ),
        )
        self.add_function(
            self._web_read,
            name="web_read",
            description=(
                "Fetch a web page and extract its main text content. "
                "Returns the extracted text or an error message."
            ),
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _web_search(self, query: str, num_results: int = 5) -> str:
        """Search the web via DuckDuckGo and return numbered markdown results.

        Args:
            query: Search query string.
            num_results: Maximum number of results to return.

        Returns:
            Numbered markdown list of results, or an informative message.

        Raises:
            ImportError: If ``duckduckgo_search`` is not installed.
        """
        if DDGS is None:
            msg = (
                "duckduckgo_search is not installed. Install with: uv add 'duckduckgo-search>=7.0'"
            )
            raise ImportError(msg)

        def _do_search() -> list[dict[str, str]]:
            return DDGS().text(keywords=query, max_results=num_results)  # type: ignore[misc]

        try:
            raw_results: list[dict[str, str]] = await asyncio.to_thread(_do_search)
        except Exception as exc:
            if _RatelimitException is not None and isinstance(exc, _RatelimitException):
                return "Rate limited. Try again in a few seconds."
            raise

        # Filter through URL safety check.
        safe_results: list[dict[str, str]] = []
        for r in raw_results:
            try:
                self._check_url(r.get("href", ""))
                safe_results.append(r)
            except ValueError:
                continue

        if not safe_results:
            return f"No results found for: {query}"

        lines: list[str] = []
        for i, result in enumerate(safe_results, 1):
            title = result.get("title", "Untitled")
            href = result.get("href", "")
            body = result.get("body", "")
            lines.append(f"{i}. [{title}]({href})\n{body}")

        return "\n\n".join(lines)

    async def _web_read(self, url: str, max_length: int = 50_000) -> str:
        """Fetch a web page and extract its main text content.

        Args:
            url: The URL to fetch and extract content from.
            max_length: Maximum number of characters in the returned text.

        Returns:
            Extracted text content, or an error/fallback message.

        Raises:
            ValueError: If the URL is blocked by the safety check.
        """
        self._check_url(url)

        @TRANSIENT_RETRY
        async def _fetch_url(target: str) -> httpx.Response:
            async with httpx.AsyncClient() as client:
                resp = await client.get(target, timeout=30, follow_redirects=True)
                resp.raise_for_status()
            return resp

        try:
            response = await _fetch_url(url)
        except httpx.TimeoutException:
            return f"Timeout fetching {url}"
        except httpx.HTTPStatusError as exc:
            return f"HTTP {exc.response.status_code}: {url}"
        except httpx.HTTPError as exc:
            return f"Error fetching page: {error_to_user_message(exc)}"

        content = extract_content(response.text, url=url).text
        if content:
            return content[:max_length]

        # Empty extraction falls back to raw HTML.
        if not content:
            # Fallback: raw HTML text truncated to max_length
            content = response.text[:max_length]

        result = content[:max_length]

        from owlbear.config import OwlBearSettings  # noqa: PLC0415

        if OwlBearSettings().wrap_web_content:
            from owlbear.core.content_safety import wrap_untrusted_content  # noqa: PLC0415

            result = wrap_untrusted_content(result, source_url=url)

        return result
