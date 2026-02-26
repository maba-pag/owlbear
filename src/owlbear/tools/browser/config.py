"""Browser configuration model.

Defines :class:`BrowserConfig` — a frozen Pydantic model that holds
launch options, viewport size, timeout, and URL allow/block lists
(validated as compilable regular expressions).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator, model_validator


class BrowserConfig(BaseModel, frozen=True):
    """Configuration for the browser automation tool.

    Attributes:
        allowed_urls: Regex patterns for URLs the browser may navigate to.
            An empty list means *all* URLs are allowed (subject to blocklist).
        blocked_urls: Regex patterns for URLs the browser must never visit.
        headless: Whether to launch the browser without a visible window.
        viewport: ``(width, height)`` in pixels.  Both must be positive.
        timeout_ms: Navigation timeout in milliseconds.  Must be >= 0.
    """

    allowed_urls: list[str] = []
    blocked_urls: list[str] = []
    headless: bool = False
    viewport: tuple[int, int] = (1280, 720)
    timeout_ms: int = 30_000

    # --- validators ---

    @field_validator("allowed_urls", "blocked_urls", mode="before")
    @classmethod
    def _validate_regex_patterns(cls, patterns: list[str], info: object) -> list[str]:
        """Ensure every pattern is a compilable regular expression."""
        for idx, pattern in enumerate(patterns):
            try:
                re.compile(pattern)
            except re.error as exc:
                field = getattr(info, "field_name", "urls")
                msg = f"Item {idx} in {field} is not a valid regex: {exc}"
                raise ValueError(msg) from exc
        return patterns

    @field_validator("timeout_ms", mode="after")
    @classmethod
    def _timeout_non_negative(cls, value: int) -> int:
        """Timeout must be zero or positive."""
        if value < 0:
            msg = "timeout_ms must be >= 0"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _viewport_positive(self) -> BrowserConfig:
        """Both viewport dimensions must be strictly positive."""
        w, h = self.viewport
        if w <= 0 or h <= 0:
            msg = "viewport width and height must be positive integers"
            raise ValueError(msg)
        return self
