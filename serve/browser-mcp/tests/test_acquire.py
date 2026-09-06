"""Behavioral tests for the MCP browser acquisition boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_browser import AcquisitionStatus, AcquisitionSuccess, Diagnostics
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import AppContext, acquire


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
async def test_acquire_delegates_exact_allowlisted_private_fixture() -> None:
    """An exact internal hostname can reach the synthetic private acquisition fixture."""
    url = "http://internal.fixture.test/page"
    launcher = MagicMock()
    launcher.acquire = AsyncMock(
        return_value=AcquisitionSuccess(
            status=AcquisitionStatus.SUCCESS,
            requested_url=url,
            canonical_url=url,
            redirect_chain=(url,),
            title="Internal fixture",
            markdown="Internal fixture content",
            discovered_links=(),
            content_hash="internal-fixture-hash",
            fetched_at=datetime.now(UTC),
            diagnostics=Diagnostics("complete"),
        )
    )
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["internal.fixture.test"]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    with patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("10.0.0.7", 80))]):
        result = await acquire(ctx, url)

    request = launcher.acquire.await_args.args[0]
    assert request.url == url
    assert result["status"] == "success"
    assert result["markdown"] == "Internal fixture content"


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
