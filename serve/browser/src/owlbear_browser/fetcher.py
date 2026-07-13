"""BrowserContentFetcher — rendered content acquisition via Playwright."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

from owlbear_browser.contract import (
    AcquisitionFailure,
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
    AcquisitionSuccess,
    Diagnostics,
    content_hash,
    normalize_links,
    normalize_markdown,
)
from owlbear_browser.extractor import extract_content


class BrowserContentFetcher:
    """ContentFetcher implementation backed by a Playwright BrowserContext."""

    def __init__(self, context: BrowserContext) -> None:
        self._context = context

    async def fetch(self, request: AcquisitionRequest | str) -> AcquisitionResult | str:
        """Acquire stable rendered content, or preserve the legacy string API."""
        if isinstance(request, str):
            page = await self._context.new_page()
            try:
                await page.goto(request, wait_until="domcontentloaded")
                return extract_content(await page.content(), request)
            finally:
                await page.close()

        return await self.acquire(request)

    async def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:  # noqa: C901, PLR0911, PLR0912, PLR0915
        page = await self._context.new_page()
        redirect_chain: list[str] = []

        def observe(response: object) -> None:
            response_url = getattr(response, "url", None)
            if isinstance(response_url, str) and (not redirect_chain or redirect_chain[-1] != response_url):
                redirect_chain.append(response_url)

        page.on("response", observe)
        try:
            try:
                response = await page.goto(
                    request.url,
                    wait_until="domcontentloaded",
                    timeout=request.navigation_timeout_ms,
                )
            except Exception as error:  # noqa: BLE001
                return AcquisitionFailure(
                    AcquisitionStatus.NAVIGATION_FAILED,
                    Diagnostics("navigation", {"error": type(error).__name__}),
                )
            disposition = response.headers.get("content-disposition", "") if response is not None else ""
            if disposition.lower().startswith("attachment"):
                return AcquisitionFailure(
                    AcquisitionStatus.DOWNLOAD_REJECTED,
                    Diagnostics("navigation", {"url": page.url}),
                )
            try:
                if request.readiness_selector:
                    await page.wait_for_selector(request.readiness_selector, timeout=request.readiness_timeout_ms)
                deadline = time.monotonic() + request.readiness_timeout_ms / 1000
                previous_text = ""
                stable_observations = 0
                required_stable_observations = 2
                stabilized = False
                while time.monotonic() < deadline:
                    selector = request.content_selector or request.readiness_selector or "body"
                    current_text = await page.locator(selector).first.inner_text()
                    if current_text.strip() and current_text == previous_text:
                        stable_observations += 1
                        if stable_observations >= required_stable_observations:
                            stabilized = True
                            break
                    else:
                        stable_observations = 0
                    previous_text = current_text
                    await asyncio.sleep(0.05)
                if not stabilized:
                    raise TimeoutError  # noqa: TRY301
            except Exception as error:  # noqa: BLE001
                return AcquisitionFailure(
                    AcquisitionStatus.CONTENT_NOT_READY,
                    Diagnostics("readiness", {"error": type(error).__name__, "selector": request.readiness_selector}),
                )

            final_url = page.url
            if urlparse(final_url).scheme not in {"http", "https"}:
                return AcquisitionFailure(
                    AcquisitionStatus.UNSUPPORTED_TARGET,
                    Diagnostics("validation", {"url": final_url}),
                )
            page_text = (await page.locator("body").inner_text()).lower()
            if re.search(r"(?:sign in|log in|authentication required|consent required)", page_text):
                return AcquisitionFailure(
                    AcquisitionStatus.AUTHENTICATION_REQUIRED,
                    Diagnostics("validation", {"url": final_url}),
                )
            if re.search(r"(?:access denied|forbidden|insufficient permission)", page_text):
                return AcquisitionFailure(
                    AcquisitionStatus.ACCESS_DENIED,
                    Diagnostics("validation", {"url": final_url}),
                )
            region = page.locator(request.content_selector) if request.content_selector else page.locator("body")
            if await region.count() == 0:
                return AcquisitionFailure(
                    AcquisitionStatus.SELECTOR_NOT_FOUND,
                    Diagnostics("selection", {"selector": request.content_selector}),
                )
            rendered_html = await region.first.inner_html()
            if not rendered_html.strip():
                return AcquisitionFailure(
                    AcquisitionStatus.SELECTOR_NOT_FOUND,
                    Diagnostics("selection", {"selector": request.content_selector}),
                )
            markdown = normalize_markdown(extract_content(rendered_html, final_url))
            if not markdown:
                return AcquisitionFailure(AcquisitionStatus.EXTRACTION_FAILED, Diagnostics("extraction"))
            links = await region.first.locator("a[href]").evaluate_all("els => els.map(el => el.href)")
            return AcquisitionSuccess(
                AcquisitionStatus.SUCCESS,
                request.url,
                final_url,
                tuple(redirect_chain[:-1]),
                await page.title(),
                markdown,
                normalize_links(links, final_url),
                content_hash(markdown),
                datetime.now(UTC),
                Diagnostics("complete", {"response_status": response.status if response else None}),
            )
        finally:
            await page.close()
