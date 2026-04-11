"""OwlBear MCP browser server — browser-control tools with domain allowlist."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_browser.allowlist import DomainAllowlist

__all__ = ["mcp_app"]


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    allowlist: DomainAllowlist


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
    """Configure DomainAllowlist and yield AppContext for the MCP session."""
    _apply_tool_exclusions(server)
    domains_env = os.environ.get("BROWSER_ALLOWED_DOMAINS", "")
    domains = [d.strip() for d in domains_env.split(",") if d.strip()]
    allowlist = DomainAllowlist(domains=domains)
    yield AppContext(allowlist=allowlist)


_mcp = FastMCP("owlbear-mcp-browser", lifespan=app_lifespan)


@_mcp.tool()
async def navigate(url: str) -> str:
    """Navigate the browser to *url*."""
    domains_env = os.environ.get("BROWSER_ALLOWED_DOMAINS", "")
    domains = [d.strip() for d in domains_env.split(",") if d.strip()]
    allowlist = DomainAllowlist(domains=domains)
    try:
        allowlist.check(url)
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc
    return url


@_mcp.tool()
async def click(selector: str) -> str:
    """Click the element identified by *selector*."""
    return selector


@_mcp.tool(name="type")
async def type_input(selector: str, text: str) -> str:
    """Type *text* into the element identified by *selector*."""
    return f"{selector}:{text}"


@_mcp.tool()
async def select(selector: str, value: str) -> str:
    """Select *value* in the element identified by *selector*."""
    return f"{selector}:{value}"


@_mcp.tool()
async def read_text() -> str:
    """Read the visible text content of the current page."""
    return ""


@_mcp.tool()
async def snapshot() -> str:
    """Take an accessibility snapshot of the current page as Markdown."""
    return ""


# Synchronous tool registry for inspection and testing (ToolManager.list_tools is sync)
mcp_app = _mcp._tool_manager  # noqa: SLF001
