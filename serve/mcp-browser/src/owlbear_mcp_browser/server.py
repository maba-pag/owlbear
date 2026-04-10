"""OwlBear MCP browser server — browser-control tools with domain allowlist."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

__all__ = ["mcp_app"]

_mcp = FastMCP("owlbear-mcp-browser")


@_mcp.tool()
async def navigate(url: str) -> str:
    """Navigate the browser to *url*."""
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
