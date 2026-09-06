"""Behavioral tests for the MCP browser acquisition boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_browser import AcquisitionStatus, AcquisitionSuccess, Diagnostics
from owlbear_browser.playwright_launcher import PlaywrightLauncher
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import AppContext, acquire


class _InternalFixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><main>Internal fixture content</main></body></html>")

    def log_message(self, *_args: object) -> None:
        return


@pytest.mark.asyncio
async def test_acquire_delegates_allowed_public_url_after_security_checks() -> None:
    """Allowed public acquisition passes SSRF and domain checks before delegation."""
    url = "https://target.example.com/delayed"
    launcher = MagicMock()
    launcher.acquire = AsyncMock(
        return_value=AcquisitionSuccess(
            status=AcquisitionStatus.SUCCESS,
            requested_url=url,
            canonical_url=url,
            redirect_chain=(url,),
            title="Delayed fixture",
            markdown="Rendered fixture content",
            discovered_links=(),
            content_hash="fixture-hash",
            fetched_at=datetime.now(UTC),
            diagnostics=Diagnostics("complete"),
        )
    )
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["target.example.com"]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 443))]):
        result = await acquire(ctx, url)

    request = launcher.acquire.await_args.args[0]
    assert request.url == url
    assert result["status"] == "success"
    assert result["markdown"] == "Rendered fixture content"


@pytest.mark.asyncio
@pytest.mark.browser
async def test_acquire_delegates_exact_allowlisted_private_fixture(tmp_path: Path) -> None:
    """An exact internal hostname can reach the synthetic private acquisition fixture."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _InternalFixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://localhost:{server.server_port}/page"
    try:
        async with PlaywrightLauncher(user_data_dir=str(tmp_path / "profile"), headless=True) as launcher:
            app_ctx = AppContext(allowlist=DomainAllowlist(domains=["localhost"]), launcher=launcher)
            ctx = MagicMock()
            ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)
            result = await acquire(ctx, url)
    finally:
        server.shutdown()
        server.server_close()

    assert result["status"] == "success"
    assert result["requested_url"] == url
    assert result["canonical_url"] == url
    assert "Internal fixture content" in result["markdown"]


@pytest.mark.asyncio
async def test_acquire_rejects_a_domain_outside_the_allowlist() -> None:
    """Acquisition does not delegate when the requested hostname is not allowed."""
    launcher = MagicMock()
    launcher.acquire = AsyncMock()
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["allowed.example.com"]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with (
        patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 443))]),
        pytest.raises(ToolError, match="not in allowlist"),
    ):
        await acquire(ctx, "https://blocked.example.com/page")

    launcher.acquire.assert_not_awaited()


@pytest.mark.asyncio
async def test_acquire_wildcard_allows_public_domains_but_not_private_targets() -> None:
    """Wildcard testing mode still relies on the SSRF check for private targets."""
    url = "https://public.example.com/page"
    launcher = MagicMock()
    launcher.acquire = AsyncMock(
        return_value=AcquisitionSuccess(
            status=AcquisitionStatus.SUCCESS,
            requested_url=url,
            canonical_url=url,
            redirect_chain=(url,),
            title="Public page",
            markdown="Public page content",
            discovered_links=(),
            content_hash="public-hash",
            fetched_at=datetime.now(UTC),
            diagnostics=Diagnostics("complete"),
        )
    )
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["*"]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 443))]):
        await acquire(ctx, url)
    launcher.acquire.assert_awaited_once()

    with (
        patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("127.0.0.1", 443))]),
        pytest.raises(ToolError, match="blocked IP address"),
    ):
        await acquire(ctx, "https://localhost/page")
