"""OwlBear root exception.

All custom OwlBear exceptions inherit from :class:`OwlBearError` so that
``except OwlBearError`` catches any OwlBear-originated error without
catching third-party or stdlib exceptions.

See ``docs/research/exception-hierarchy.md`` for design rationale.
"""

from __future__ import annotations


class OwlBearError(Exception):
    """Root base class for all OwlBear-specific exceptions."""


class BlockedURLError(OwlBearError):
    """Raised when a navigation URL is denied by the safety guard.

    Attributes:
        url: The URL that was blocked.
        pattern: The regex pattern that matched (or ``"<not in allowlist>"``).
    """

    def __init__(self, url: str, pattern: str) -> None:
        self.url = url
        self.pattern = pattern
        super().__init__(f"URL blocked by pattern {pattern!r}: {url}")
