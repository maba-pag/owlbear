"""Crawl configuration model.

Defines :class:`CrawlConfig` — a frozen Pydantic model that holds
crawl options: seed URLs, depth/page limits, domain scoping, politeness
settings, and URL allow/deny patterns (validated as compilable regexes).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


class CrawlConfig(BaseModel, frozen=True):
    """Configuration for web crawl operations.

    Attributes:
        seed_urls: Starting URLs to crawl (required, non-empty).
        max_depth: Maximum link-follow depth from seed pages (>= 0).
        max_pages: Maximum total pages to crawl (>= 1).
        same_domain_only: Whether to restrict crawling to seed domains.
        allow_patterns: Regex patterns; only matching URLs are crawled.
        deny_patterns: Regex patterns; matching URLs are skipped.
        delay_seconds: Politeness delay between requests in seconds (>= 0).
        respect_robots: Whether to obey ``robots.txt`` directives.
        user_agent: User-Agent string sent with requests.
    """

    seed_urls: list[str]
    max_depth: int = 1
    max_pages: int = 50
    same_domain_only: bool = True
    allow_patterns: list[str] = []
    deny_patterns: list[str] = []
    delay_seconds: float = 1.5
    respect_robots: bool = True
    user_agent: str = "OwlBear/1.0 (research crawler)"
    cache_ttl_seconds: int = 86400

    # --- validators ---

    @field_validator("seed_urls", mode="after")
    @classmethod
    def _seed_urls_non_empty(cls, value: list[str]) -> list[str]:
        """seed_urls must contain at least one URL."""
        if not value:
            msg = "seed_urls must not be empty"
            raise ValueError(msg)
        return value

    @field_validator("max_depth", mode="after")
    @classmethod
    def _max_depth_non_negative(cls, value: int) -> int:
        """max_depth must be >= 0."""
        if value < 0:
            msg = "max_depth must be >= 0"
            raise ValueError(msg)
        return value

    @field_validator("max_pages", mode="after")
    @classmethod
    def _max_pages_at_least_one(cls, value: int) -> int:
        """max_pages must be >= 1."""
        if value < 1:
            msg = "max_pages must be >= 1"
            raise ValueError(msg)
        return value

    @field_validator("delay_seconds", mode="after")
    @classmethod
    def _delay_non_negative(cls, value: float) -> float:
        """delay_seconds must be >= 0."""
        if value < 0:
            msg = "delay_seconds must be >= 0"
            raise ValueError(msg)
        return value

    @field_validator("cache_ttl_seconds", mode="after")
    @classmethod
    def _cache_ttl_non_negative(cls, value: int) -> int:
        """cache_ttl_seconds must be >= 0."""
        if value < 0:
            msg = "cache_ttl_seconds must be >= 0"
            raise ValueError(msg)
        return value

    @field_validator("allow_patterns", "deny_patterns", mode="before")
    @classmethod
    def _validate_regex_patterns(cls, patterns: list[str], info: object) -> list[str]:
        """Ensure every pattern is a compilable regular expression."""
        for idx, pattern in enumerate(patterns):
            try:
                re.compile(pattern)
            except re.error as exc:
                field = getattr(info, "field_name", "patterns")
                msg = f"Item {idx} in {field} is not a valid regex: {exc}"
                raise ValueError(msg) from exc
        return patterns
