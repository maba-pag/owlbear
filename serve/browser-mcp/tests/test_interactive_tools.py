"""Behavioral tests for browser-control tools that require a live page."""

from __future__ import annotations

import socket
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import AppContext, click, mcp, navigate, read_text, select, snapshot, type_input

_URL = "https://target.example.com/page"
_TYPED_TEXT = "sensitive input"
_PUBLIC_ADDRESS_INFO = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
_TOOLS_AND_ARGUMENTS = [
    pytest.param(navigate, (_URL,), id="navigate"),
    pytest.param(click, ("#submit",), id="click"),
    pytest.param(type_input, ("#password", _TYPED_TEXT), id="type_input"),
    pytest.param(select, ("#choice", "selected"), id="select"),
    pytest.param(read_text, (), id="read_text"),
    pytest.param(snapshot, (), id="snapshot"),
]
_ACTION_TOOLS_AND_ARGUMENTS = _TOOLS_AND_ARGUMENTS[:4]
_READER_TOOLS = [pytest.param(read_text, id="read_text"), pytest.param(snapshot, id="snapshot")]


def _tool_context(app_ctx: object) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _fake_page() -> MagicMock:
    page = MagicMock()
    page.is_closed.return_value = False
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html><body><main>Rendered browser page</main></body></html>")
    page.url = _URL
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.select_option = AsyncMock()
    locator.aria_snapshot = AsyncMock(return_value="heading: Browser page")
    page.locator.return_value = locator
    return page


def _live_context(page: MagicMock) -> MagicMock:
    app_ctx = AppContext(
        allowlist=DomainAllowlist(domains=["target.example.com"]),
        launcher=MagicMock(),
        page=page,
    )
    return _tool_context(app_ctx)


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", _READER_TOOLS)
@pytest.mark.parametrize("availability", ["startup-failed", "no-session", "non-app-context"])
async def test_reader_tools_raise_without_live_page_and_never_launch(
    tool: Callable[..., Awaitable[str]],
    availability: str,
) -> None:
    if availability == "startup-failed":
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["target.example.com"]),
            browser_diagnostic="browser startup failed (RuntimeError)",
        )
        expected_error = "Browser unavailable"
    elif availability == "no-session":
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=["target.example.com"]))
        app_ctx.last_content = "cached content"
        expected_error = "No browser session"
    else:
        app_ctx = SimpleNamespace(
            allowlist=DomainAllowlist(domains=["target.example.com"]),
            page=_fake_page(),
            last_content="cached content",
        )
        expected_error = "Browser unavailable"

    with (
        patch("owlbear_browser_mcp.server.PlaywrightLauncher") as factory,
        pytest.raises(ToolError, match=expected_error),
    ):
        await tool(_tool_context(app_ctx))

    factory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool", "arguments"), _ACTION_TOOLS_AND_ARGUMENTS)
async def test_action_tools_reject_non_app_context_without_touching_page(
    tool: Callable[..., Awaitable[str]],
    arguments: tuple[str, ...],
) -> None:
    page = _fake_page()
    app_ctx = SimpleNamespace(allowlist=DomainAllowlist(domains=["target.example.com"]), page=page)

    with (
        patch("socket.getaddrinfo", return_value=_PUBLIC_ADDRESS_INFO) as mock_dns,
        pytest.raises(ToolError, match="Browser unavailable") as error,
    ):
        await tool(_tool_context(app_ctx), *arguments)

    mock_dns.assert_not_called()
    assert _URL not in str(error.value)
    page.goto.assert_not_awaited()
    page.locator.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(("tool", "arguments"), _ACTION_TOOLS_AND_ARGUMENTS)
async def test_action_tools_launch_on_demand_and_report_safe_launch_failure(
    tool: Callable[..., Awaitable[str]],
    arguments: tuple[str, ...],
) -> None:
    app_ctx = AppContext(allowlist=DomainAllowlist(domains=["target.example.com"]))
    launcher = MagicMock()
    launcher.launch = AsyncMock(side_effect=RuntimeError("/private/profile"))
    launcher.close = AsyncMock()

    with (
        patch("owlbear_browser_mcp.server.PlaywrightLauncher", return_value=launcher) as factory,
        patch("socket.getaddrinfo", return_value=_PUBLIC_ADDRESS_INFO),
        pytest.raises(ToolError, match=r"Browser unavailable: browser startup failed \(RuntimeError\)") as error,
    ):
        await tool(_tool_context(app_ctx), *arguments)

    factory.assert_called_once()
    launcher.close.assert_awaited_once()
    assert "/private/profile" not in str(error.value)
    assert _URL not in str(error.value)


@pytest.mark.asyncio
async def test_navigate_uses_live_page_and_returns_extracted_content() -> None:
    page = _fake_page()
    ctx = _live_context(page)

    with patch("socket.getaddrinfo", return_value=_PUBLIC_ADDRESS_INFO):
        result = await navigate(ctx, _URL)

    page.goto.assert_awaited_once_with(_URL, wait_until="domcontentloaded")
    assert "Rendered browser page" in result
    assert "<html>" not in result
    assert result != _URL


@pytest.mark.asyncio
async def test_click_select_and_type_input_use_live_locators_without_echoing_text() -> None:
    page = _fake_page()
    ctx = _live_context(page)
    locator = page.locator.return_value

    assert await click(ctx, "#submit") == "#submit"
    assert await select(ctx, "#choice", "selected") == "#choice:selected"
    result = await type_input(ctx, "#password", _TYPED_TEXT)

    locator.click.assert_awaited_once_with()
    locator.select_option.assert_awaited_once_with("selected")
    locator.fill.assert_awaited_once_with(_TYPED_TEXT)
    assert result == "#password"
    assert _TYPED_TEXT not in result


@pytest.mark.asyncio
async def test_read_text_and_snapshot_use_live_page_output() -> None:
    page = _fake_page()
    ctx = _live_context(page)

    text = await read_text(ctx)
    aria_snapshot = await snapshot(ctx)

    assert "Rendered browser page" in text
    assert aria_snapshot == "heading: Browser page"
    page.content.assert_awaited_once()
    page.locator.assert_called_once_with("body")
    page.locator.return_value.aria_snapshot.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_interactive_tool_names_and_annotations_match_their_contracts() -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert set(tools) == {"acquire", "navigate", "click", "type_input", "select", "read_text", "snapshot"}
    assert tools["click"].annotations == ToolAnnotations(
        read_only_hint=False, idempotent_hint=False, destructive_hint=True
    )
    assert tools["type_input"].annotations == ToolAnnotations(
        read_only_hint=False, idempotent_hint=True, destructive_hint=False
    )
    assert tools["select"].annotations == ToolAnnotations(
        read_only_hint=False, idempotent_hint=True, destructive_hint=False
    )
    for name in ("read_text", "snapshot"):
        assert tools[name].annotations == ToolAnnotations(
            read_only_hint=True, idempotent_hint=True, destructive_hint=False
        )
