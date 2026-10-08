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
from owlbear_browser_mcp.server import AppContext, acquire, app_lifespan, click, mcp, read_text, snapshot


class _FakePage:
    def __init__(self, calls: list[str], *, error: BaseException | None = None) -> None:
        self._calls = calls
        self._error = error
        self.closed = False
        self.clicked: list[str] = []

    def is_closed(self) -> bool:
        return self.closed

    def locator(self, selector: str) -> _FakePage:
        self.clicked.append(selector)
        return self

    async def click(self) -> None:
        return

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
        self.is_running = False

    async def launch(self) -> None:
        self._calls.append("launch")
        await asyncio.sleep(0)
        if self._launch_error is not None:
            raise self._launch_error
        self.is_running = True

    async def page(self) -> _FakePage:
        self._calls.append("page-create")
        if self._page_error is not None:
            raise self._page_error
        if self._page_resource is not None and not self._page_resource.closed:
            return self._page_resource
        return _FakePage(self._calls)

    async def close(self) -> None:
        self._calls.append("launcher")
        self.is_running = False


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


def _tool_ctx(context: object) -> SimpleNamespace:
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))


@pytest.mark.asyncio
async def test_startup_and_reader_tools_do_not_launch_the_browser() -> None:
    calls: list[str] = []

    with patch.object(server_module, "PlaywrightLauncher", side_effect=lambda **_: _FakeLauncher(calls)) as factory:
        async with app_lifespan(mcp) as context:
            for reader in (read_text, snapshot):
                with pytest.raises(ToolError, match="No browser session"):
                    await reader(_tool_ctx(context))

    factory.assert_not_called()
    assert calls == []


@pytest.mark.asyncio
async def test_concurrent_first_tool_calls_launch_once_and_shutdown_closes_it() -> None:
    calls: list[str] = []

    with patch.object(server_module, "PlaywrightLauncher", side_effect=lambda **_: _FakeLauncher(calls)) as factory:
        async with app_lifespan(mcp) as context:
            await asyncio.gather(click(_tool_ctx(context), "#a"), click(_tool_ctx(context), "#b"))

    factory.assert_called_once()
    assert calls == ["launch", "page-create", "page", "launcher"]
    assert context.page is None
    assert context.launcher is None


@pytest.mark.asyncio
async def test_closed_page_is_reopened_without_relaunching() -> None:
    calls: list[str] = []

    with patch.object(server_module, "PlaywrightLauncher", side_effect=lambda **_: _FakeLauncher(calls)) as factory:
        async with app_lifespan(mcp) as context:
            await click(_tool_ctx(context), "#a")
            first_page = context.page
            first_page.closed = True
            with pytest.raises(ToolError, match="No browser session"):
                await read_text(_tool_ctx(context))
            await click(_tool_ctx(context), "#b")
            assert context.page is not first_page

    factory.assert_called_once()
    assert calls == ["launch", "page-create", "page-create", "page", "launcher"]


@pytest.mark.asyncio
async def test_closed_browser_is_relaunched_and_only_current_resources_close_at_shutdown() -> None:
    calls: list[str] = []
    launchers: list[_FakeLauncher] = []

    def make_launcher(**_: object) -> _FakeLauncher:
        launchers.append(_FakeLauncher(calls))
        return launchers[-1]

    with patch.object(server_module, "PlaywrightLauncher", side_effect=make_launcher):
        async with app_lifespan(mcp) as context:
            await click(_tool_ctx(context), "#a")
            launchers[0].is_running = False
            await click(_tool_ctx(context), "#b")
            assert context.launcher is launchers[1]
            calls.append("shutdown")

    assert calls == ["launch", "page-create", "launcher", "launch", "page-create", "shutdown", "page", "launcher"]


@pytest.mark.asyncio
async def test_launch_failure_reports_safe_diagnostic_and_next_call_retries() -> None:
    calls: list[str] = []
    launchers = [
        _FakeLauncher(calls, page_error=RuntimeError("/private/profile/token")),
        _FakeLauncher(calls),
    ]

    with patch.object(server_module, "PlaywrightLauncher", side_effect=launchers):
        async with app_lifespan(mcp) as context:
            with pytest.raises(
                ToolError, match=r"Browser unavailable: browser startup failed \(RuntimeError\)"
            ) as error:
                await click(_tool_ctx(context), "#a")
            assert "/private/profile/token" not in str(error.value)
            assert context.launcher is None
            assert context.page is None
            with pytest.raises(ToolError, match=r"Browser unavailable: browser startup failed"):
                await read_text(_tool_ctx(context))

            await click(_tool_ctx(context), "#b")
            assert context.launcher is launchers[1]
            assert context.browser_diagnostic is None

    assert calls == ["launch", "page-create", "launcher", "launch", "page-create", "page", "launcher"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure_stage", "error"),
    [
        ("launch", asyncio.CancelledError()),
        ("page", asyncio.CancelledError()),
        ("launch", KeyboardInterrupt()),
    ],
)
async def test_launch_control_flow_failure_closes_launcher_and_reraises(
    failure_stage: str, error: BaseException
) -> None:
    calls: list[str] = []
    launcher = _FakeLauncher(
        calls,
        launch_error=error if failure_stage == "launch" else None,
        page_error=error if failure_stage == "page" else None,
    )

    with patch.object(server_module, "PlaywrightLauncher", return_value=launcher):
        async with app_lifespan(mcp) as context:
            with pytest.raises(type(error)):
                await click(_tool_ctx(context), "#a")
            assert context.launcher is None

    expected_calls = ["launch", "launcher"]
    if failure_stage == "page":
        expected_calls.insert(1, "page-create")
    assert calls == expected_calls


@pytest.mark.asyncio
async def test_shutdown_attempts_page_and_launcher_cleanup_after_page_failure() -> None:
    calls: list[str] = []
    page = _FakePage(calls, error=RuntimeError("page cleanup failed"))
    launcher = _FakeLauncher(calls, page_resource=page)

    with patch.object(server_module, "PlaywrightLauncher", return_value=launcher):
        async with app_lifespan(mcp) as context:
            await click(_tool_ctx(context), "#a")
            assert context.page is page

    assert calls == ["launch", "page-create", "page", "launcher"]
    assert context.page is None
    assert context.launcher is None


@pytest.mark.asyncio
async def test_shutdown_defers_page_cancellation_until_launcher_cleanup() -> None:
    calls: list[str] = []
    page = _FakePage(calls, error=asyncio.CancelledError())
    launcher = _FakeLauncher(calls, page_resource=page)

    contexts: list[AppContext] = []

    async def use_browser() -> None:
        async with app_lifespan(mcp) as context:
            contexts.append(context)
            await click(_tool_ctx(context), "#a")
            assert context.page is page

    with (
        patch.object(server_module, "PlaywrightLauncher", return_value=launcher),
        pytest.raises(asyncio.CancelledError),
    ):
        await use_browser()

    context = contexts[0]

    assert calls == ["launch", "page-create", "page", "launcher"]
    assert context.page is None
    assert context.launcher is None


def test_launcher_reports_not_running_after_context_close_event() -> None:
    launcher = PlaywrightLauncher()
    assert not launcher.is_running
    launcher._context = object()  # type: ignore[assignment]  # noqa: SLF001
    assert launcher.is_running
    launcher._mark_context_closed(launcher._context)  # noqa: SLF001
    assert not launcher.is_running


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
async def test_acquire_rejects_blocked_destination_before_launching() -> None:
    context = AppContext(allowlist=DomainAllowlist(domains=["example.com"]))

    with (
        patch.object(server_module, "PlaywrightLauncher") as factory,
        patch("socket.getaddrinfo", return_value=[("AF_INET", 0, 0, "", ("93.184.216.34", 443))]),
        pytest.raises(ToolError, match="not in allowlist"),
    ):
        await acquire(_tool_ctx(context), "https://blocked.example.org")

    factory.assert_not_called()
