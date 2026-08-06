"""Behavioral tests for the MCP browser acquisition boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_browser import AcquisitionStatus, AcquisitionSuccess, Diagnostics
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import AppContext, acquire


@pytest.mark.asyncio
async def test_acquire_delegates_explicit_loopback_url_without_interactive_policy() -> None:
    """Explicit HTTP(S) acquisition authorizes private and loopback targets."""
    url = "http://127.0.0.1:8421/delayed"
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
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), launcher=launcher)
    ctx = MagicMock()
    ctx.request_context = SimpleNamespace(lifespan_context=app_ctx)

    result = await acquire(ctx, url)

    request = launcher.acquire.await_args.args[0]
    assert request.url == url
    assert result["status"] == "success"
    assert result["markdown"] == "Rendered fixture content"
