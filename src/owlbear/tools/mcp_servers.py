"""MCP server factory functions — GitHub, Git, Fetch.

Each factory returns a configured :class:`MCPServerStdio` instance
ready for registration in :class:`MCPServerRegistry`.  The convenience
function :func:`register_default_servers` wires all three into a
registry using values from :class:`OwlBearSettings`.

Usage::

    from owlbear.tools.mcp_servers import register_default_servers
    register_default_servers(registry, settings)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.mcp import MCPServerStdio

if TYPE_CHECKING:
    from owlbear.config import OwlBearSettings
    from owlbear.tools.mcp_registry import MCPServerRegistry

__all__ = [
    "fetch_mcp_server",
    "git_mcp_server",
    "github_mcp_server",
    "register_default_servers",
]


def github_mcp_server(token: str) -> MCPServerStdio:
    """Return an MCPServerStdio for the GitHub MCP server.

    Args:
        token: GitHub personal access token.

    Returns:
        Configured :class:`MCPServerStdio` instance.
    """
    return MCPServerStdio(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
        tool_prefix="github",
    )


def git_mcp_server() -> MCPServerStdio:
    """Return an MCPServerStdio for the Git MCP server.

    No environment variables are needed — operates on local repos only.

    .. note::

        Uses ``tool_prefix='git_mcp'`` to avoid naming conflicts with
        the native :class:`GitLocalToolset` which already uses the
        ``git_`` prefix for its tool names.

    Returns:
        Configured :class:`MCPServerStdio` instance.
    """
    return MCPServerStdio(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-git"],
        tool_prefix="git_mcp",
    )


def fetch_mcp_server() -> MCPServerStdio:
    """Return an MCPServerStdio for the Fetch MCP server.

    The server handles robots.txt compliance natively — no additional
    configuration is required.

    Returns:
        Configured :class:`MCPServerStdio` instance.
    """
    return MCPServerStdio(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-fetch"],
        tool_prefix="fetch",
    )


def register_default_servers(
    registry: MCPServerRegistry,
    settings: OwlBearSettings,
) -> None:
    """Register the default MCP servers into *registry*.

    Registers GitHub (if a token is configured), Git, and Fetch servers.

    Args:
        registry: Target :class:`MCPServerRegistry`.
        settings: Application settings providing ``github_token``.
    """
    if settings.github_token:
        registry.register(
            "github",
            github_mcp_server(settings.github_token.get_secret_value()),
        )
    registry.register("git", git_mcp_server())
    registry.register("fetch", fetch_mcp_server())
