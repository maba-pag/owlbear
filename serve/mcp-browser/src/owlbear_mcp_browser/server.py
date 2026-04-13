"""OwlBear MCP browser server — browser-control tools with domain allowlist."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from owlbear_browser.cdp import CDPConnectionManager
    from owlbear_browser.fetcher import BrowserContentFetcher

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_browser._errors import AuthenticationRequired
from owlbear_browser.cdp import CDPConnectionManager as _CDPConnectionManager
from owlbear_browser.extractor import extract_content
from owlbear_mcp_browser.allowlist import DomainAllowlist

__all__ = ["AppContext", "app_lifespan", "mcp_app"]


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    allowlist: DomainAllowlist
    cdp: CDPConnectionManager | None = None
    page: Any = None
    fetcher: BrowserContentFetcher | None = None
    last_content: str = ""


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read BROWSER_TOOLS_EXCLUDE and remove each listed tool from the server.

    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    env_val = os.environ.get("BROWSER_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Configure DomainAllowlist, attempt CDP connection, and yield AppContext."""
    _apply_tool_exclusions(server)
    domains_env = os.environ.get("BROWSER_ALLOWED_DOMAINS", "")
    domains = [d.strip() for d in domains_env.split(",") if d.strip()]
    allowlist = DomainAllowlist(domains=domains)

    cdp: _CDPConnectionManager | None = None
    page: Any = None
    try:
        manager = _CDPConnectionManager()
        await manager.connect()
        cdp = manager
        contexts = manager._browser.contexts  # noqa: SLF001
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
    except Exception:  # noqa: BLE001
        cdp = None
        page = None

    try:
        yield AppContext(allowlist=allowlist, cdp=cdp, page=page)
    finally:
        if cdp is not None:
            await cdp.disconnect()


_MSG_NO_PAGE = "Browser not available: no active page session"

_mcp = FastMCP("owlbear-mcp-browser", lifespan=app_lifespan)


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def navigate(ctx: Context, url: str) -> str:
    """Navigate the browser to *url*."""
    app_ctx = ctx.request_context.lifespan_context
    try:
        app_ctx.allowlist.check(url)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc

    if not isinstance(app_ctx, AppContext):
        return url

    if app_ctx.page is not None:
        await app_ctx.page.goto(url)
        return url

    if app_ctx.fetcher is not None:
        try:
            content = await app_ctx.fetcher.fetch(url)
        except AuthenticationRequired as exc:
            msg = f"SSO session expired or authentication required: {exc}"
            raise ToolError(msg) from exc
        app_ctx.last_content = content
        return content

    return url


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False))
async def click(ctx: Context, selector: str) -> str:
    """Click the element identified by *selector*."""
    page = getattr(ctx.request_context.lifespan_context, "page", None)
    if page is not None:
        await page.locator(selector).click()
    return selector


@_mcp.tool(name="type", annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False))
async def type_input(ctx: Context, selector: str, text: str) -> str:
    """Type *text* into the element identified by *selector*."""
    page = getattr(ctx.request_context.lifespan_context, "page", None)
    if page is not None:
        await page.locator(selector).fill(text)
    return f"{selector}:{text}"


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def select(ctx: Context, selector: str, value: str) -> str:
    """Select *value* in the element identified by *selector*."""
    page = getattr(ctx.request_context.lifespan_context, "page", None)
    if page is not None:
        await page.locator(selector).select_option(value)
    return f"{selector}:{value}"


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def read_text(ctx: Context) -> str:
    """Read the visible text content of the current page."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is not None:
        html = await page.content()
        return extract_content(html, page.url)
    _missing = object()
    last_content = getattr(app_ctx, "last_content", _missing)
    if last_content is not _missing:
        return last_content  # type: ignore[return-value]
    raise ToolError(_MSG_NO_PAGE)


@_mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def snapshot(ctx: Context) -> str:
    """Take an accessibility snapshot of the current page as Markdown."""
    app_ctx = ctx.request_context.lifespan_context
    page = getattr(app_ctx, "page", None)
    if page is None:
        return getattr(app_ctx, "last_content", "")
    return await page.aria_snapshot()


# Synchronous tool registry for inspection and testing (ToolManager.list_tools is sync)
mcp_app = _mcp._tool_manager  # noqa: SLF001
