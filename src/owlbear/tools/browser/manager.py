"""Browser lifecycle manager.

Provides :class:`BrowserManager` — an async context manager that
launches a Playwright Chromium instance, creates a browser context and
page, and tears everything down on exit (even when exceptions occur).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

from owlbear.tools.browser.config import BrowserConfig

if TYPE_CHECKING:
    from types import TracebackType

    from playwright.async_api import Browser, BrowserContext, Page, Playwright

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    async_playwright = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class BrowserManager:
    """Async context manager for a Playwright Chromium browser.

    Usage::

        async with BrowserManager() as mgr:
            page = mgr.page
            await page.goto("https://example.com")

    On entry, launches Chromium with the settings from *config*.
    On exit, closes page → context → browser → Playwright in reverse
    order, guaranteeing cleanup even when an exception propagates.
    """

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # -- public API --

    @property
    def page(self) -> Page:
        """The active Playwright page.

        Raises:
            RuntimeError: If accessed outside the ``async with`` block.
        """
        if self._page is None:
            msg = "BrowserManager is not entered — use 'async with' first"
            raise RuntimeError(msg)
        return self._page

    # -- async context manager protocol --

    async def __aenter__(self) -> Self:
        if async_playwright is None:  # pragma: no cover
            msg = "playwright is not installed — install it with: uv pip install 'owlbear[browser]'"
            raise ImportError(msg)

        pw_cm = async_playwright()
        self._pw = await pw_cm.start()
        self._browser = await self._pw.chromium.launch(headless=self._config.headless)
        w, h = self._config.viewport
        self._context = await self._browser.new_context(viewport={"width": w, "height": h})
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self._config.timeout_ms)
        logger.debug("BrowserManager: Chromium launched (headless=%s)", self._config.headless)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if self._page is not None:
                await self._page.close()
        finally:
            try:
                if self._context is not None:
                    await self._context.close()
            finally:
                try:
                    if self._browser is not None:
                        await self._browser.close()
                finally:
                    if self._pw is not None:
                        await self._pw.stop()
        logger.debug("BrowserManager: all resources closed")
