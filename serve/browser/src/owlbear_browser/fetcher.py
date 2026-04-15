"""BrowserContentFetcher — authenticated fetch via Playwright."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

from owlbear_browser.extractor import extract_content


class BrowserContentFetcher:
    """ContentFetcher implementation backed by a Playwright BrowserContext."""

    def __init__(self, context: BrowserContext) -> None:
        self._context = context

    async def fetch(self, url: str) -> str:
        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            html: str = await page.content()
            return extract_content(html, url)
        finally:
            await page.close()
