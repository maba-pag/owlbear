from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import ClassVar

import pytest

from owlbear_browser import (
    AcquisitionFailure,
    AcquisitionRequest,
    AcquisitionStatus,
    AcquisitionSuccess,
    BrowserContentFetcher,
)

pytestmark = pytest.mark.browser


class _FixtureHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[str]] = []

    def do_GET(self) -> None:  # noqa: C901, PLR0911, PLR0915
        self.requests.append(self.path)
        if self.path == "/start":
            self.send_response(302)
            self.send_header("Location", "/page")
            self.end_headers()
            return
        if self.path == "/linked":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"linked")
            return
        if self.path == "/download":
            self.send_response(200)
            self.send_header("Content-Disposition", "attachment; filename=fixture.txt")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"download")
            return
        if self.path == "/auth":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><form><input type='email'>Sign in</form></body></html>")
            return
        if self.path == "/protected":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'<html><body><main id="content">Protected content</main></body></html>')
            return
        if self.path == "/denied":
            self.send_response(403)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Access denied</body></html>")
            return
        if self.path == "/unrelated":
            self.send_response(302)
            self.send_header("Location", "https://example.com/other")
            self.end_headers()
            return
        if self.path == "/empty":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Ready<main id='content'></main></body></html>")
            return
        if self.path == "/false-positive":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><main id='content'>Our guide explains how to sign in.</main></body></html>")
            return
        if self.path == "/ambiguous":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><title>Unexpected page</title><body>Rendered but unclassified</body></html>")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b'<html><title>Fixture</title><body><main id="content">'
            b'<h1>Rendered title</h1><p id="delayed"></p>'
            b'<a href="/linked#one">first</a><a href="/linked#two">duplicate</a>'
            b'<a href="mailto:test@example.com">mail</a></main>'
            b'<link rel="stylesheet" href="/style.css">'
            b'<script>setTimeout(() => document.querySelector("#delayed").textContent = "Stable body", 80)</script>'
            b"</body></html>"
        )

    def log_message(self, *_args: object) -> None:
        return


@pytest.mark.asyncio
async def test_acquire_waits_for_rendered_content_and_keeps_links_inert() -> None:
    _FixtureHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            result = await BrowserContentFetcher(context).acquire(
                AcquisitionRequest(
                    f"http://127.0.0.1:{server.server_port}/start",
                    content_selector="#content",
                    readiness_timeout_ms=2_000,
                )
            )
            await browser.close()
        assert isinstance(result, AcquisitionSuccess)
        assert result.status is AcquisitionStatus.SUCCESS
        assert result.requested_url == f"http://127.0.0.1:{server.server_port}/start"
        assert result.canonical_url.endswith("/page")
        assert result.redirect_chain == (f"http://127.0.0.1:{server.server_port}/start",)
        assert result.title == "Fixture"
        assert "Stable body" in result.markdown
        assert result.discovered_links == (f"http://127.0.0.1:{server.server_port}/linked",)
        assert result.content_hash
        assert result.fetched_at.tzinfo is not None
        assert result.diagnostics.stage == "complete"
        assert "/linked" not in _FixtureHandler.requests
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_status", "expected_status"),
    [
        (404, AcquisitionStatus.HTTP_ERROR),
        (500, AcquisitionStatus.HTTP_ERROR),
        (401, AcquisitionStatus.ACCESS_DENIED),
        (403, AcquisitionStatus.ACCESS_DENIED),
        (200, AcquisitionStatus.SUCCESS),
    ],
)
async def test_acquire_classifies_main_document_http_statuses(
    response_status: int, expected_status: AcquisitionStatus
) -> None:
    from playwright.async_api import Route, async_playwright  # noqa: PLC0415

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            context = await browser.new_context()

            async def fulfill_document(route: Route) -> None:
                await route.fulfill(
                    status=response_status,
                    content_type="text/html",
                    body='<html><body><main id="content">Rendered document</main></body></html>',
                )

            await context.route("http://pages.synthetic.example/**", fulfill_document)
            result = await BrowserContentFetcher(context).acquire(
                AcquisitionRequest(
                    "http://pages.synthetic.example/page",
                    content_selector="#content",
                    readiness_timeout_ms=2_000,
                )
            )
        finally:
            await browser.close()

    if expected_status is AcquisitionStatus.HTTP_ERROR:
        assert isinstance(result, AcquisitionFailure)
        assert result.status is AcquisitionStatus.HTTP_ERROR
        assert result.diagnostics.stage == "navigation"
        assert result.diagnostics.details == {"response_status": response_status}
    elif expected_status is AcquisitionStatus.ACCESS_DENIED:
        assert isinstance(result, AcquisitionFailure)
        assert result.status is AcquisitionStatus.ACCESS_DENIED
    else:
        assert isinstance(result, AcquisitionSuccess)
        assert result.status is AcquisitionStatus.SUCCESS
        assert result.markdown.strip()


@pytest.mark.asyncio
async def test_authentication_page_stays_open_and_retry_reuses_it() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from owlbear_browser.playwright_launcher import PlaywrightLauncher  # noqa: PLC0415

        async with PlaywrightLauncher(headless=True) as launcher:
            auth_url = f"http://127.0.0.1:{server.server_port}/auth"
            result = await launcher.acquire(AcquisitionRequest(auth_url))
            assert result.status is AcquisitionStatus.AUTHENTICATION_REQUIRED
            retry = await launcher.acquire(
                AcquisitionRequest(
                    f"http://127.0.0.1:{server.server_port}/protected",
                    content_selector="#content",
                    readiness_timeout_ms=200,
                )
            )
        assert isinstance(retry, AcquisitionSuccess)
        assert retry.markdown == "Protected content"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_acquire_reports_missing_content_selector() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            result = await BrowserContentFetcher(context).acquire(
                AcquisitionRequest(
                    f"http://127.0.0.1:{server.server_port}/page",
                    content_selector='a[href="https://example.test/cb?code=abc123#private"]',
                    readiness_timeout_ms=200,
                )
            )
            await browser.close()
        assert result.status is AcquisitionStatus.SELECTOR_NOT_FOUND
        assert result.diagnostics.details == {"selector": "content_selector"}
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/auth", AcquisitionStatus.AUTHENTICATION_REQUIRED),
        ("/denied", AcquisitionStatus.ACCESS_DENIED),
        ("/unrelated", AcquisitionStatus.REDIRECT_REJECTED),
        ("/empty", AcquisitionStatus.EXTRACTION_FAILED),
        ("/ambiguous", AcquisitionStatus.AMBIGUOUS_FINAL_PAGE),
    ],
)
async def test_acquire_rejects_invalid_final_page_states(path: str, expected_status: AcquisitionStatus) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            request = AcquisitionRequest(
                f"http://127.0.0.1:{server.server_port}{path}",
                content_selector="#content" if path == "/empty" else None,
                readiness_selector="body" if path == "/empty" else None,
                readiness_timeout_ms=5_000,
            )
            result = await BrowserContentFetcher(context).acquire(request)
            await browser.close()
        assert result.status is expected_status
        assert result.diagnostics.details.get("signal") or expected_status is AcquisitionStatus.EXTRACTION_FAILED
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_acquire_does_not_misclassify_login_terminology() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            result = await BrowserContentFetcher(context).acquire(
                AcquisitionRequest(f"http://127.0.0.1:{server.server_port}/false-positive")
            )
            await browser.close()
        assert isinstance(result, AcquisitionSuccess)
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_acquire_reports_unsupported_target_at_public_boundary() -> None:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        fetcher = BrowserContentFetcher(context)
        result = await fetcher.acquire(AcquisitionRequest("file:///tmp/page.html"))
        relative = await fetcher.acquire(AcquisitionRequest("/cb?code=abc123#private"))
        await browser.close()
    assert result.status is AcquisitionStatus.UNSUPPORTED_TARGET
    assert relative.status is AcquisitionStatus.UNSUPPORTED_TARGET
    assert relative.diagnostics.details == {"reason": "unsupported_url"}


@pytest.mark.asyncio
async def test_acquire_rejects_download_navigation() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            result = await BrowserContentFetcher(context).acquire(
                AcquisitionRequest(f"http://127.0.0.1:{server.server_port}/download")
            )
            await browser.close()
        assert result.status is AcquisitionStatus.DOWNLOAD_REJECTED
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_selector", "readiness_selector", "expected_status"),
    [
        ("#missing-content", None, AcquisitionStatus.SELECTOR_NOT_FOUND),
        ("#content", "#missing", AcquisitionStatus.CONTENT_NOT_READY),
    ],
)
async def test_acquire_reports_unready_content(
    content_selector: str, readiness_selector: str | None, expected_status: AcquisitionStatus
) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            result = await BrowserContentFetcher(context).acquire(
                AcquisitionRequest(
                    f"http://127.0.0.1:{server.server_port}/page",
                    content_selector=content_selector,
                    readiness_selector=readiness_selector,
                    readiness_timeout_ms=100,
                )
            )
            await browser.close()
        assert result.status is expected_status
    finally:
        server.shutdown()
        server.server_close()
