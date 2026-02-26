"""Browser lifecycle manager.

Provides :class:`BrowserManager` — an async context manager that
launches a Playwright Chromium instance (or connects to an existing
browser via CDP), creates a page, and tears everything down on exit
(even when exceptions occur).
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

    Supports two modes:

    * **Launch mode** (default) — launches a new Chromium instance.
    * **CDP mode** — connects to an existing browser via
      ``config.cdp_endpoint`` using the Chrome DevTools Protocol.

    Usage::

        async with BrowserManager() as mgr:
            page = mgr.page
            await page.goto("https://example.com")

    On entry, launches Chromium (or connects via CDP) with the settings
    from *config*.  On exit, guarantees cleanup even when an exception
    propagates.
    """

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._is_cdp: bool = False
        self._owned_pages: list[Page] = []

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

        if self._config.cdp_endpoint:
            await self._enter_cdp()
        else:
            await self._enter_launch()

        self._page.set_default_timeout(self._config.timeout_ms)
        return self

    async def _enter_cdp(self) -> None:
        """Connect to an existing browser via CDP endpoint."""
        try:
            self._browser = await self._pw.chromium.connect_over_cdp(  # type: ignore[union-attr]
                self._config.cdp_endpoint,
            )
        except Exception as exc:
            await self._pw.stop()  # type: ignore[union-attr]
            self._pw = None
            msg = f"Cannot connect to CDP endpoint {self._config.cdp_endpoint}"
            raise ConnectionError(msg) from exc

        self._is_cdp = True
        self._context = self._browser.contexts[0]
        self._page = await self._context.new_page()
        self._owned_pages.append(self._page)
        logger.debug("BrowserManager: connected via CDP to %s", self._config.cdp_endpoint)

    async def _enter_launch(self) -> None:
        """Launch a new Chromium instance."""
        self._is_cdp = False
        self._browser = await self._pw.chromium.launch(headless=self._config.headless)  # type: ignore[union-attr]
        w, h = self._config.viewport
        self._context = await self._browser.new_context(viewport={"width": w, "height": h})
        self._page = await self._context.new_page()
        self._owned_pages.append(self._page)
        logger.debug("BrowserManager: Chromium launched (headless=%s)", self._config.headless)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._is_cdp:
            await self._exit_cdp()
        else:
            await self._exit_launch()
        logger.debug("BrowserManager: all resources closed")

    async def _exit_cdp(self) -> None:
        """CDP cleanup: close owned pages → disconnect → stop Playwright."""
        try:
            for page in self._owned_pages:
                await page.close()
        finally:
            try:
                if self._browser is not None:
                    await self._browser.disconnect()
            finally:
                if self._pw is not None:
                    await self._pw.stop()

    async def _exit_launch(self) -> None:
        """Launch cleanup: page → context → browser → stop Playwright."""
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
