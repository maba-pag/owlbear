"""Lifecycle failure and cleanup contracts for the Browser MCP server."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_browser.playwright_launcher import AuthenticationCapabilities, PlaywrightLauncher
from owlbear_browser_mcp import server as server_module
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import AppContext, acquire, app_lifespan, mcp


class _FakePage:
    def __init__(self, calls: list[str], *, error: Exception | None = None) -> None:
        self._calls = calls
        self._error = error

    async def close(self) -> None:
        self._calls.append("page")
        if self._error is not None:
            raise self._error


class _FakeLauncher:
    def __init__(self, calls: list[str], *, page_error: Exception | None = None) -> None:
        self._calls = calls
        self._page_error = page_error

    async def launch(self) -> None:
        self._calls.append("launch")

    async def page(self) -> _FakePage:
        self._calls.append("page-create")
        if self._page_error is not None:
            raise self._page_error
        return _FakePage(self._calls)

    async def close(self) -> None:
        self._calls.append("launcher")


class _AsyncResource:
    def __init__(self, name: str, calls: list[str], *, error: Exception | None = None) -> None:
        self._name = name
        self._calls = calls
        self._error = error

    async def close(self) -> None:
        self._calls.append(self._name)
        if self._error is not None:
            raise self._error


class _AsyncPlaywright:
    def __init__(self, calls: list[str], *, error: Exception | None = None) -> None:
        self._calls = calls
        self._error = error

    async def stop(self) -> None:
        self._calls.append("playwright")
        if self._error is not None:
            raise self._error


@pytest.mark.asyncio
async def test_startup_page_failure_closes_launcher_and_exposes_safe_diagnostic() -> None:
    calls: list[str] = []
    launcher = _FakeLauncher(calls, page_error=RuntimeError("/private/profile/token"))

    with patch.object(server_module, "PlaywrightLauncher", return_value=launcher):
        async with app_lifespan(mcp) as context:
            assert context.launcher is None
            assert context.page is None
            assert context.browser_diagnostic == "browser startup failed (RuntimeError)"
            assert "/private/profile/token" not in context.browser_diagnostic
            ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))
            with pytest.raises(ToolError, match=r"Browser unavailable: browser startup failed \(RuntimeError\)"):
                await acquire(ctx, "https://example.com")

    assert calls == ["launch", "page-create", "launcher"]


@pytest.mark.asyncio
async def test_shutdown_attempts_page_and_launcher_cleanup_after_page_failure() -> None:
    calls: list[str] = []
    launcher = _FakeLauncher(calls)
    page = _FakePage(calls, error=RuntimeError("page cleanup failed"))

    with patch.object(server_module, "PlaywrightLauncher", return_value=launcher):
        async with app_lifespan(mcp) as context:
            context.page = page

    assert calls == ["launch", "page-create", "page", "launcher"]


@pytest.mark.asyncio
async def test_launcher_close_attempts_all_resources_and_is_idempotent() -> None:
    calls: list[str] = []
    launcher = PlaywrightLauncher()
    launcher._fetcher = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "fetcher", calls, error=RuntimeError("fetcher failed")
    )
    launcher._context = _AsyncResource("context", calls)  # type: ignore[assignment]  # noqa: SLF001
    launcher._pw = _AsyncPlaywright(calls)  # noqa: SLF001
    launcher._capabilities = AuthenticationCapabilities(  # noqa: SLF001
        persistent_session=True,
        visible_manual_auth=True,
        microsoft_sso=True,
    )

    with pytest.raises(RuntimeError, match="fetcher failed"):
        await launcher.close()

    assert calls == ["fetcher", "context", "playwright"]
    assert launcher._fetcher is None  # noqa: SLF001
    assert launcher._context is None  # noqa: SLF001
    assert launcher._pw is None  # noqa: SLF001
    assert launcher.capabilities == AuthenticationCapabilities(
        persistent_session=False,
        visible_manual_auth=False,
        microsoft_sso=False,
    )

    await launcher.close()
    assert calls == ["fetcher", "context", "playwright"]


@pytest.mark.asyncio
async def test_app_context_without_browser_diagnostic_keeps_no_page_message() -> None:
    context = AppContext(allowlist=DomainAllowlist(domains=["example.com"]))
    ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))

    with pytest.raises(ToolError, match="No browser session"):
        await acquire(ctx, "https://example.com")