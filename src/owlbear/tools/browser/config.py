"""Browser configuration model.

Defines :class:`BrowserConfig` — a frozen Pydantic model that holds
launch options, viewport size, timeout, and URL allow/block lists
(validated as compilable regular expressions).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator, model_validator

_MAX_PORT = 65535


class BrowserConfig(BaseModel, frozen=True):
    """Configuration for the browser automation tool.

    Attributes:
        allowed_urls: Regex patterns for URLs the browser may navigate to.
            An empty list means *all* URLs are allowed (subject to blocklist).
        blocked_urls: Regex patterns for URLs the browser must never visit.
        headless: Whether to launch the browser without a visible window.
        viewport: ``(width, height)`` in pixels.  Both must be positive.
        timeout_ms: Navigation timeout in milliseconds.  Must be >= 0.
        cdp_endpoint: CDP HTTP endpoint URL (localhost/127.0.0.1 only).
        cdp_port: Default CDP debugging port (1-65535).
        browser_executable: Override path for the browser binary.
        auto_launch: Whether to auto-launch browser if CDP unavailable.
    """

    allowed_urls: list[str] = []
    blocked_urls: list[str] = []
    headless: bool = False
    viewport: tuple[int, int] = (1280, 720)
    timeout_ms: int = 30_000
    cdp_endpoint: str | None = None
    cdp_port: int = 9222
    browser_executable: str | None = None
    auto_launch: bool = True

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

    @field_validator("cdp_endpoint", mode="after")
    @classmethod
    def _cdp_endpoint_localhost_only(cls, value: str | None) -> str | None:
        """CDP endpoint must be http://localhost or http://127.0.0.1."""
        if value is None:
            return value
        try:
            parsed = urlparse(value)
        except Exception as exc:
            msg = "cdp_endpoint is not a valid URL"
            raise ValueError(msg) from exc
        if parsed.scheme != "http":
            msg = "cdp_endpoint must use http:// scheme"
            raise ValueError(msg)
        if parsed.hostname not in ("localhost", "127.0.0.1"):
            msg = "cdp_endpoint must target localhost or 127.0.0.1"
            raise ValueError(msg)
        return value

    @field_validator("cdp_port", mode="after")
    @classmethod
    def _cdp_port_valid_range(cls, value: int) -> int:
        """CDP port must be between 1 and 65535 inclusive."""
        if not (1 <= value <= _MAX_PORT):
            msg = f"cdp_port must be between 1 and {_MAX_PORT}"
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
