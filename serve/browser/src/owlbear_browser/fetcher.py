"""BrowserContentFetcher — authenticated fetch via CDP."""

from __future__ import annotations

from owlbear_browser.extractor import extract_content


class BrowserContentFetcher:
    """ContentFetcher implementation backed by a live CDPConnectionManager."""

    def __init__(self, cdp: object) -> None:
        self._cdp = cdp

    async def fetch(self, url: str) -> str:
        page = await self._cdp._browser.contexts[0].new_page()  # type: ignore[attr-defined]  # noqa: SLF001
        try:
            await page.goto(url)
            await self._cdp.check_sso_redirect(page)  # type: ignore[attr-defined]
            html: str = await page.content()
            return extract_content(html, url)
        finally:
            await page.close()
