"""Behavioral tests for the MCP browser acquisition boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_browser import AcquisitionFailure, AcquisitionStatus, AcquisitionSuccess, Diagnostics
from owlbear_browser.playwright_launcher import PlaywrightLauncher
from owlbear_browser_mcp import server as server_module
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import (
    AppContext,
    _serialize_acquisition,
    acquire,
    browser_status,
    mcp,
    navigate,
)


class _InternalFixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(404 if self.path.startswith("/not-found") else 200)
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

    assert (await browser_status(ctx))["latest_acquisition_status"] is None
    with patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 443))]):
        result = await acquire(ctx, url)

    request = launcher.acquire.await_args.args[0]
    assert request.url == url
    assert result["status"] == "success"
    assert result["markdown"] == "Rendered fixture content"
    assert app_ctx.latest_acquisition_status is AcquisitionStatus.SUCCESS
    assert (await browser_status(ctx))["latest_acquisition_status"] == AcquisitionStatus.SUCCESS.value


@pytest.mark.asyncio
async def test_first_acquire_lazily_launches_managed_edge() -> None:
    url = "https://target.example.com/page"
    page = MagicMock()
    page.close = AsyncMock()
    launcher = MagicMock()
    launcher.is_running = False

    async def start_launcher() -> None:
        launcher.is_running = True

    launcher.launch = AsyncMock(side_effect=start_launcher)
    launcher.page = AsyncMock(return_value=page)
    launcher.acquire = AsyncMock(
        return_value=AcquisitionFailure(
            status=AcquisitionStatus.ACCESS_DENIED,
            diagnostics=Diagnostics("denied"),
        )
    )
    launcher.close = AsyncMock()

    with (
        patch.object(server_module.sys, "platform", "darwin"),
        patch.dict(
            server_module.os.environ,
            {"BROWSER_ALLOWED_DOMAINS": "target.example.com"},
            clear=True,
        ),
        patch.object(server_module, "_check_ssrf", new_callable=AsyncMock) as ssrf_check,
        patch.object(server_module, "PlaywrightLauncher", return_value=launcher) as launcher_factory,
    ):
        async with server_module.app_lifespan(mcp) as context:
            ctx = MagicMock()
            ctx.request_context = SimpleNamespace(lifespan_context=context)
            assert (await browser_status(ctx))["startup_state"] == "not-launched"
            launcher_factory.assert_not_called()

            result = await acquire(ctx, url)

            assert result["status"] == "access_denied"
            assert context.page is page
            status = await browser_status(ctx)
            assert status["browser_mode"] == "managed-edge"
            assert status["startup_state"] == "ready"
            assert status["startup_reason"] is None
            assert status["startup_diagnostic"] is None
            assert launcher_factory.call_count == 1
            assert launcher_factory.call_args.kwargs["mode"].value == "managed-edge"
            assert launcher_factory.call_args.kwargs["user_data_dir"] == context.user_data_dir
            ssrf_check.assert_awaited_once()

    launcher.launch.assert_awaited_once()
    launcher.page.assert_awaited_once()
    launcher.acquire.assert_awaited_once()
    launcher.close.assert_awaited_once()
    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquisition_failure_updates_status_and_fresh_context_starts_empty() -> None:
    url = "https://target.example.com/failure"
    launcher = MagicMock()
    launcher.acquire = AsyncMock(
        return_value=AcquisitionFailure(
            status=AcquisitionStatus.ACCESS_DENIED,
            diagnostics=Diagnostics("denied"),
        )
    )
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["target.example.com"]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)
    with patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 443))]):
        result = await acquire(ctx, url)
    assert result["status"] == "access_denied"
    assert app_ctx.latest_acquisition_status is AcquisitionStatus.ACCESS_DENIED
    assert (await browser_status(ctx))["latest_acquisition_status"] == AcquisitionStatus.ACCESS_DENIED.value
    assert AppContext(allowlist=DomainAllowlist(domains=["example.com"])).latest_acquisition_status is None


def test_mcp_serialization_redacts_all_acquisition_url_surfaces() -> None:
    url = "https://user:secret@example.test/page?code=oauth-code&state=csrf&view=full#fragment"
    result = AcquisitionSuccess(
        status=AcquisitionStatus.SUCCESS,
        requested_url=url,
        canonical_url=url,
        redirect_chain=(url,),
        title="Title",
        markdown="# Content",
        discovered_links=(url,),
        content_hash="fixture-hash",
        fetched_at=datetime.now(UTC),
        diagnostics=Diagnostics("complete"),
    )

    serialized = _serialize_acquisition(result)

    assert (
        serialized["requested_url"] == "https://example.test/page?code=%5BREDACTED%5D&state=%5BCORRELATION%5D&view=full"
    )
    assert serialized["canonical_url"] == serialized["requested_url"]
    assert serialized["redirect_chain"] == [serialized["requested_url"]]
    assert serialized["discovered_links"] == [serialized["requested_url"]]
    assert "html" not in serialized["diagnostics"]


@pytest.mark.asyncio
async def test_acquire_schema_does_not_advertise_removed_diagnostic_html_option() -> None:
    with patch("owlbear_browser_mcp.server.PlaywrightLauncher") as launcher_factory:
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert "include_diagnostic_html" not in tools["acquire"].input_schema["properties"]
    launcher_factory.assert_not_called()


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("address", "expected_error"),
    [("93.184.216.34", None), ("127.0.0.1", "blocked IP address")],
)
async def test_acquire_uses_app_context_resolver(address: str, expected_error: str | None) -> None:
    """Injected resolution controls SSRF checks without consulting the system resolver."""
    url = "http://pages.synthetic.example/a"
    launcher = MagicMock()
    launcher.acquire = AsyncMock(
        return_value=AcquisitionSuccess(
            status=AcquisitionStatus.SUCCESS,
            requested_url=url,
            canonical_url=url,
            redirect_chain=(url,),
            title="Synthetic page",
            markdown="Synthetic content",
            discovered_links=(),
            content_hash="synthetic-hash",
            fetched_at=datetime.now(UTC),
            diagnostics=Diagnostics("complete"),
        )
    )
    resolver = MagicMock(return_value=[("AF_INET", 0, 0, "", (address, 80))])
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["*"]), launcher=launcher, resolver=resolver)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with patch("socket.getaddrinfo") as system_resolver:
        if expected_error is not None:
            with pytest.raises(ToolError, match=expected_error):
                await acquire(ctx, url)
            launcher.acquire.assert_not_awaited()
        else:
            result = await acquire(ctx, url)
            assert result["status"] == "success"
            launcher.acquire.assert_awaited_once()
            assert launcher.acquire.await_args.args[0].url == url

    resolver.assert_called_once_with("pages.synthetic.example", 80)
    system_resolver.assert_not_called()


@pytest.mark.asyncio
async def test_acquire_default_resolver_looks_up_socket_getaddrinfo_at_call_time() -> None:
    """An AppContext without an override uses the current socket.getaddrinfo."""
    url = "http://pages.synthetic.example/a"
    launcher = MagicMock()
    launcher.acquire = AsyncMock(
        return_value=AcquisitionSuccess(
            status=AcquisitionStatus.SUCCESS,
            requested_url=url,
            canonical_url=url,
            redirect_chain=(url,),
            title="Synthetic page",
            markdown="Synthetic content",
            discovered_links=(),
            content_hash="synthetic-hash",
            fetched_at=datetime.now(UTC),
            diagnostics=Diagnostics("complete"),
        )
    )
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["*"]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 80))]) as system_resolver:
        result = await acquire(ctx, url)

    assert result["status"] == "success"
    system_resolver.assert_called_once_with("pages.synthetic.example", 80)
    launcher.acquire.assert_awaited_once()


@pytest.mark.asyncio
async def test_navigate_uses_app_context_resolver_before_navigation() -> None:
    """Injected resolution blocks private destinations before page navigation."""
    page = MagicMock()
    page.goto = AsyncMock()
    resolver = MagicMock(return_value=[("AF_INET", 0, 0, "", ("127.0.0.1", 80))])
    app_ctx = AppContext(
        allowlist=DomainAllowlist(domains=["*"]),
        launcher=MagicMock(),
        page=page,
        resolver=resolver,
    )
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with patch("socket.getaddrinfo") as system_resolver, pytest.raises(ToolError, match="blocked IP address"):
        await navigate(ctx, "http://pages.synthetic.example/a")

    resolver.assert_called_once_with("pages.synthetic.example", 80)
    system_resolver.assert_not_called()
    page.goto.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.browser
async def test_acquire_projects_http_error_without_query_secret(tmp_path: Path) -> None:
    """A real 404 acquisition includes its status but not its query token in the tool result."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _InternalFixtureHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://localhost:{server.server_port}/not-found?token=secret"
    try:
        async with PlaywrightLauncher(user_data_dir=str(tmp_path / "profile"), headless=True) as launcher:
            app_ctx = AppContext(allowlist=DomainAllowlist(domains=["localhost"]), launcher=launcher)
            ctx = MagicMock()
            ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)
            result = await acquire(ctx, url, content_selector="main")
    finally:
        server.shutdown()
        server.server_close()

    assert result["status"] == "http_error"
    assert result["diagnostics"]["details"]["response_status"] == 404
    assert "secret" not in json.dumps(result)
