"""BrowserContentFetcher — rendered content acquisition via Playwright."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

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
        self._pending_page: Page | None = None

    async def close(self) -> None:
        """Close a page retained for manual authentication."""
        if self._pending_page is not None and not self._pending_page.is_closed():
            await self._pending_page.close()
        self._pending_page = None

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
        """Acquire and validate rendered content for a structured browser request."""
        parsed_request_url = urlparse(request.url)
        if parsed_request_url.scheme.lower() not in {"http", "https"} or not parsed_request_url.netloc:
            return AcquisitionFailure(
                AcquisitionStatus.UNSUPPORTED_TARGET,
                Diagnostics("validation", {"url": request.url}),
            )
        page = self._pending_page or await self._context.new_page()
        self._pending_page = None
        keep_page_open = False
        download_detected = False

        def observe_download(_download: object) -> None:
            nonlocal download_detected
            download_detected = True

        page.on("download", observe_download)
        try:
            try:
                response = await page.goto(
                    request.url,
                    wait_until="domcontentloaded",
                    timeout=request.navigation_timeout_ms,
                )
            except Exception as error:  # noqa: BLE001
                if download_detected or "download" in str(error).lower():
                    return AcquisitionFailure(
                        AcquisitionStatus.DOWNLOAD_REJECTED,
                        Diagnostics("navigation", {"url": page.url}),
                    )
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
                region = page.locator(request.content_selector) if request.content_selector else page.locator("body")
                if request.content_selector and await region.count() == 0:
                    return AcquisitionFailure(
                        AcquisitionStatus.SELECTOR_NOT_FOUND,
                        Diagnostics("selection", {"selector": request.content_selector}),
                    )
                if request.readiness_selector:
                    await page.wait_for_selector(request.readiness_selector, timeout=request.readiness_timeout_ms)
                deadline = time.monotonic() + request.readiness_timeout_ms / 1000
                previous_text = ""
                stable_observations = 0
                required_stable_observations = 2
                stabilized = False
                while time.monotonic() < deadline:
                    selector = request.readiness_selector or request.content_selector or "body"
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
                    if request.content_selector and not previous_text.strip():
                        return AcquisitionFailure(
                            AcquisitionStatus.SELECTOR_NOT_FOUND,
                            Diagnostics("selection", {"selector": request.content_selector}),
                        )
                    raise TimeoutError  # noqa: TRY301
            except Exception as error:  # noqa: BLE001
                return AcquisitionFailure(
                    AcquisitionStatus.CONTENT_NOT_READY,
                    Diagnostics("readiness", {"error": type(error).__name__, "selector": request.readiness_selector}),
                )

            final_url = page.url
            redirect_chain: list[str] = []
            document_request = response.request if response is not None else None
            while document_request is not None:
                redirect_chain.append(document_request.url)
                document_request = document_request.redirected_from
            redirect_chain.reverse()
            if urlparse(final_url).scheme not in {"http", "https"}:
                return AcquisitionFailure(
                    AcquisitionStatus.UNSUPPORTED_TARGET,
                    Diagnostics("validation", {"url": final_url}),
                )
            page_text = (await page.locator("body").inner_text()).lower()
            page_title = (await page.title()).lower()
            auth_structure = await page.locator(
                "form, input[type='password'], input[type='email'], [role='dialog']"
            ).count()
            auth_pattern = (
                r"(?:sign in|log in|authentication required|consent required|trust this device|verify your identity)"
            )
            auth_signal = re.search(auth_pattern, page_text[:4000])
            title_auth_signal = re.search(auth_pattern, page_title)
            if (auth_structure and auth_signal) or title_auth_signal:
                self._pending_page = page
                keep_page_open = True
                return AcquisitionFailure(
                    AcquisitionStatus.AUTHENTICATION_REQUIRED,
                    Diagnostics("validation", {"url": final_url, "signal": "authentication"}),
                )
            denial_signal = re.search(r"(?:access denied|forbidden|insufficient permission)", page_text[:4000])
            if (response is not None and response.status in {401, 403}) or denial_signal:
                return AcquisitionFailure(
                    AcquisitionStatus.ACCESS_DENIED,
                    Diagnostics("validation", {"url": final_url, "signal": "access_denied"}),
                )
            requested_origin = (urlparse(request.url).scheme, urlparse(request.url).netloc)
            final_origin = (urlparse(final_url).scheme, urlparse(final_url).netloc)
            if redirect_chain and requested_origin != final_origin:
                return AcquisitionFailure(
                    AcquisitionStatus.REDIRECT_REJECTED,
                    Diagnostics("validation", {"url": final_url, "signal": "unrelated_redirect"}),
                )
            semantic_content_count = await page.locator("main, article, [role='main']").count()
            if request.content_selector is None and semantic_content_count == 0:
                return AcquisitionFailure(
                    AcquisitionStatus.AMBIGUOUS_FINAL_PAGE,
                    Diagnostics("validation", {"url": final_url, "signal": "content_boundary_missing"}),
                )
            if await region.count() == 0:
                return AcquisitionFailure(
                    AcquisitionStatus.SELECTOR_NOT_FOUND,
                    Diagnostics("selection", {"selector": request.content_selector}),
                )
            rendered_html = await region.first.inner_html()
            if not rendered_html.strip():
                return AcquisitionFailure(
                    AcquisitionStatus.EXTRACTION_FAILED,
                    Diagnostics("extraction", {"signal": "empty_content"}),
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
            if not keep_page_open:
                await page.close()
