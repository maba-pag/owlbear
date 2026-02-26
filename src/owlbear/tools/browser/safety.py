"""URL safety guard for browser navigation.

Provides :class:`URLSafetyGuard` — a ``PRE_TOOL_USE`` hook that inspects
navigation requests and blocks URLs matching configured deny patterns.
Raises :class:`BlockedURLError` for denied URLs.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry
    from owlbear.tools.browser.config import BrowserConfig

logger = logging.getLogger(__name__)


class BlockedURLError(Exception):
    """Raised when a navigation URL is denied by the safety guard.

    Attributes:
        url: The URL that was blocked.
        pattern: The regex pattern that matched (or ``"<not in allowlist>"``).
    """

    def __init__(self, url: str, pattern: str) -> None:
        self.url = url
        self.pattern = pattern
        super().__init__(f"URL blocked by pattern {pattern!r}: {url}")


class URLSafetyGuard:
    """``PRE_TOOL_USE`` hook that blocks browser navigation to denied URLs.

    The guard inspects tool-call payloads for ``navigate`` calls and checks
    the target URL against :pyattr:`BrowserConfig.blocked_urls` and
    :pyattr:`BrowserConfig.allowed_urls`.

    **Evaluation order:**

    1. If ``blocked_urls`` contains a matching pattern → **block**.
    2. If ``allowed_urls`` is non-empty and no pattern matches → **block**.
    3. Otherwise → **allow**.

    Args:
        config: Browser configuration containing URL allow/block lists.
    """

    def __init__(self, config: BrowserConfig) -> None:
        self._config = config

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: object) -> None:
        """Inspect a ``PRE_TOOL_USE`` payload and block denied URLs.

        Args:
            data: Event payload — expected to be a dict with ``tool_name``
                and ``args`` keys.  Non-dict payloads are silently ignored.

        Raises:
            BlockedURLError: If the target URL is denied.
        """
        if not isinstance(data, dict):
            return

        if data.get("tool_name") != "navigate":
            return

        args = data.get("args")
        if not isinstance(args, dict):
            return

        url: str = args.get("url", "")
        if not url:
            return

        self.check_url(url)

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this guard on :pyattr:`HookEvent.PRE_TOOL_USE`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.PRE_TOOL_USE, self)

    # -- internal ------------------------------------------------------------

    def check_url(self, url: str) -> None:
        """Raise :class:`BlockedURLError` if *url* is denied."""
        # 1. Blocklist takes absolute precedence.
        for pattern in self._config.blocked_urls:
            if re.search(pattern, url):
                logger.warning("Blocked URL %r matching pattern %r", url, pattern)
                raise BlockedURLError(url, pattern)

        # 2. If an allowlist exists, URL must match at least one entry.
        if self._config.allowed_urls:
            for pattern in self._config.allowed_urls:
                if re.search(pattern, url):
                    return
            logger.warning("URL %r not in allowed patterns", url)
            raise BlockedURLError(url, "<not in allowlist>")
