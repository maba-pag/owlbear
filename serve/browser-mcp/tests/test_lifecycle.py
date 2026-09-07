"""Lifecycle failure and cleanup contracts for the Browser MCP server."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_browser.playwright_launcher import AuthenticationCapabilities, PlaywrightLauncher
from owlbear_browser_mcp import server as server_module
from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import AppContext, acquire, app_lifespan, mcp


class _FakePage:
    def __init__(self, calls: list[str], *, error: BaseException | None = None) -> None:
        self._calls = calls
        self._error = error

    async def close(self) -> None:
        self._calls.append("page")
        if self._error is not None:
            raise self._error


class _FakeLauncher:
    def __init__(
        self,
        calls: list[str],
        *,
        launch_error: BaseException | None = None,
        page_error: BaseException | None = None,
        page_resource: _FakePage | None = None,
    ) -> None:
        self._calls = calls
        self._launch_error = launch_error
        self._page_error = page_error
        self._page_resource = page_resource

    async def launch(self) -> None:
        self._calls.append("launch")
        if self._launch_error is not None:
            raise self._launch_error

    async def page(self) -> _FakePage:
        self._calls.append("page-create")
        if self._page_error is not None:
            raise self._page_error
        if self._page_resource is not None:
            return self._page_resource
        return _FakePage(self._calls)

    async def close(self) -> None:
        self._calls.append("launcher")


class _AsyncResource:
    def __init__(self, name: str, calls: list[str], *, error: BaseException | None = None) -> None:
        self._name = name
        self._calls = calls
        self._error = error

    async def close(self) -> None:
        self._calls.append(self._name)
        if self._error is not None:
            raise self._error


class _AsyncPlaywright:
    def __init__(self, calls: list[str], *, error: BaseException | None = None) -> None:
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
async def test_startup_launch_failure_closes_launcher_and_exposes_safe_diagnostic() -> None:
    calls: list[str] = []
    launcher = _FakeLauncher(calls, launch_error=RuntimeError("/private/profile/token"))

    with patch.object(server_module, "PlaywrightLauncher", return_value=launcher):
        async with app_lifespan(mcp) as context:
            assert context.launcher is None
            assert context.page is None
            assert context.browser_diagnostic == "browser startup failed (RuntimeError)"
            assert "/private/profile/token" not in context.browser_diagnostic

    assert calls == ["launch", "launcher"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_stage", ["launch", "page"])
async def test_startup_cancellation_closes_launcher_and_reraises(failure_stage: str) -> None:
    calls: list[str] = []
    launcher = _FakeLauncher(
        calls,
        launch_error=asyncio.CancelledError() if failure_stage == "launch" else None,
        page_error=asyncio.CancelledError() if failure_stage == "page" else None,
    )

    with (
        patch.object(server_module, "PlaywrightLauncher", return_value=launcher),
        pytest.raises(asyncio.CancelledError),
    ):
        async with app_lifespan(mcp):
            pytest.fail("startup cancellation must not yield a browser context")

    expected_calls = ["launch", "launcher"]
    if failure_stage == "page":
        expected_calls.insert(1, "page-create")
    assert calls == expected_calls


@pytest.mark.asyncio
async def test_startup_keyboard_interrupt_closes_launcher_and_reraises() -> None:
    calls: list[str] = []
    launcher = _FakeLauncher(calls, launch_error=KeyboardInterrupt())

    with (
        patch.object(server_module, "PlaywrightLauncher", return_value=launcher),
        pytest.raises(KeyboardInterrupt),
    ):
        async with app_lifespan(mcp):
            pytest.fail("control-flow failure must not yield a browser context")

    assert calls == ["launch", "launcher"]


@pytest.mark.asyncio
async def test_shutdown_attempts_page_and_launcher_cleanup_after_page_failure() -> None:
    calls: list[str] = []
    page = _FakePage(calls, error=RuntimeError("page cleanup failed"))
    launcher = _FakeLauncher(calls, page_resource=page)

    with patch.object(server_module, "PlaywrightLauncher", return_value=launcher):
        async with app_lifespan(mcp) as context:
            assert context.page is page

    assert calls == ["launch", "page-create", "page", "launcher"]
    assert context.page is None
    assert context.launcher is None


@pytest.mark.asyncio
async def test_shutdown_defers_page_cancellation_until_launcher_cleanup() -> None:
    calls: list[str] = []
    page = _FakePage(calls, error=asyncio.CancelledError())
    launcher = _FakeLauncher(calls, page_resource=page)

    with (
        patch.object(server_module, "PlaywrightLauncher", return_value=launcher),
        pytest.raises(asyncio.CancelledError),
    ):
        async with app_lifespan(mcp) as context:
            assert context.page is page

    assert calls == ["launch", "page-create", "page", "launcher"]
    assert context.page is None
    assert context.launcher is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_resource", ["fetcher", "context", "playwright"])
async def test_launcher_close_attempts_all_resources_and_is_idempotent(failed_resource: str) -> None:
    calls: list[str] = []
    launcher = PlaywrightLauncher()
    launcher._fetcher = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "fetcher",
        calls,
        error=RuntimeError(f"{failed_resource} failed") if failed_resource == "fetcher" else None,
    )
    launcher._context = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "context",
        calls,
        error=RuntimeError(f"{failed_resource} failed") if failed_resource == "context" else None,
    )
    launcher._pw = _AsyncPlaywright(  # noqa: SLF001
        calls,
        error=RuntimeError(f"{failed_resource} failed") if failed_resource == "playwright" else None,
    )
    launcher._capabilities = AuthenticationCapabilities(  # noqa: SLF001
        persistent_session=True,
        visible_manual_auth=True,
        microsoft_sso=True,
    )

    with pytest.raises(RuntimeError, match=f"{failed_resource} failed"):
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
@pytest.mark.parametrize("cancelled_resource", ["fetcher", "context", "playwright"])
async def test_launcher_close_defers_cancellation_until_all_resources_attempted(cancelled_resource: str) -> None:
    calls: list[str] = []
    launcher = PlaywrightLauncher()
    launcher._fetcher = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "fetcher",
        calls,
        error=asyncio.CancelledError() if cancelled_resource == "fetcher" else None,
    )
    launcher._context = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "context",
        calls,
        error=asyncio.CancelledError() if cancelled_resource == "context" else None,
    )
    launcher._pw = _AsyncPlaywright(  # noqa: SLF001
        calls,
        error=asyncio.CancelledError() if cancelled_resource == "playwright" else None,
    )
    launcher._capabilities = AuthenticationCapabilities(  # noqa: SLF001
        persistent_session=True,
        visible_manual_auth=True,
        microsoft_sso=True,
    )

    with pytest.raises(asyncio.CancelledError):
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
async def test_launcher_close_preserves_later_cancellation_over_ordinary_error() -> None:
    calls: list[str] = []
    launcher = PlaywrightLauncher()
    launcher._fetcher = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "fetcher", calls, error=RuntimeError("fetcher failed")
    )
    launcher._context = _AsyncResource(  # type: ignore[assignment]  # noqa: SLF001
        "context", calls, error=asyncio.CancelledError()
    )
    launcher._pw = _AsyncPlaywright(calls)  # noqa: SLF001

    with pytest.raises(asyncio.CancelledError):
        await launcher.close()

    assert calls == ["fetcher", "context", "playwright"]


@pytest.mark.asyncio
async def test_app_context_without_browser_diagnostic_keeps_no_page_message() -> None:
    context = AppContext(allowlist=DomainAllowlist(domains=["example.com"]))
    ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))

    with pytest.raises(ToolError, match="No browser session"):
        await acquire(ctx, "https://example.com")
