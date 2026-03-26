"""MCP server registry — store and resolve MCP server instances by name.

Provides :class:`MCPServerRegistry` for managing named MCP server
connections (stdio or HTTP). Integrates with :class:`AgentRegistry`
via the ``mcp:`` tool-name prefix convention.

Usage::

    from owlbear.tools.mcp_registry import MCPServerRegistry
    registry = MCPServerRegistry()
    registry.register("github", MCPServerStdio(command="npx", args=[...]))
    server = registry.get("github")  # Returns the MCPServer instance
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Self

from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio, MCPServerStreamableHTTP

if TYPE_CHECKING:
    from types import TracebackType

    from pydantic_ai.mcp import MCPServer

__all__ = ["MCPServerRegistry"]

logger = logging.getLogger(__name__)

# Supported server type strings for config parsing.
_SUPPORTED_TYPES = ("stdio", "sse", "streamable_http")


class MCPServerRegistry:
    """Central registry for named MCP server instances.

    Stores :class:`MCPServerStdio` and :class:`MCPServerHTTP` instances
    by name, enabling the ``mcp:<name>`` tool-resolution prefix in
    :class:`AgentRegistry`.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServer] = {}
        self._started: set[str] = set()

    # ------------------------------------------------------------------
    # Async context-manager lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        """Start all registered MCP servers.

        Iterates over registered servers and calls ``__aenter__`` on each.
        If a server fails to start, the error is logged and the server is
        skipped — remaining servers still start.

        Returns:
            The registry instance.
        """
        for name in sorted(self._servers):
            server = self._servers[name]
            try:
                await server.__aenter__()
                self._started.add(name)
                logger.info("Started MCP server: %s", name)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to start MCP server '%s'", name, exc_info=True)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop all started MCP servers gracefully.

        Iterates over servers that were successfully started and calls
        ``__aexit__`` on each.  Errors during shutdown are logged but
        do not prevent other servers from being stopped.
        """
        for name in sorted(self._started):
            server = self._servers[name]
            try:
                await server.__aexit__(exc_type, exc_val, exc_tb)
                logger.info("Stopped MCP server: %s", name)
            except Exception:  # noqa: BLE001
                logger.warning("Error stopping MCP server '%s'", name, exc_info=True)
        self._started.clear()

    def health_check(self) -> dict[str, bool]:
        """Return liveness status for every registered server.

        A server is considered *alive* if it was successfully started
        (i.e. its ``__aenter__`` completed without error).

        Returns:
            Mapping of server name → alive boolean.
        """
        return {name: name in self._started for name in sorted(self._servers)}

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register(self, name: str, server: MCPServer) -> None:
        """Register an MCP server under *name*, overwriting any previous entry.

        Args:
            name: Short identifier (e.g. ``"github"``, ``"fetch"``).
            server: A :class:`MCPServerStdio` or :class:`MCPServerHTTP` instance.
        """
        self._servers[name] = server
        logger.debug("Registered MCP server: %s", name)

    def get(self, name: str) -> MCPServer:
        """Return the MCP server registered under *name*.

        Args:
            name: Server identifier.

        Returns:
            The :class:`MCPServer` instance.

        Raises:
            KeyError: If *name* is not registered. The error message
                includes the list of available server names.
        """
        try:
            return self._servers[name]
        except KeyError:
            available = ", ".join(sorted(self._servers))
            msg = f"MCP server '{name}' not found. Available: {available}"
            raise KeyError(msg) from None

    def names(self) -> list[str]:
        """Return sorted list of registered server names."""
        return sorted(self._servers)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> MCPServerRegistry:
        """Build a registry from a configuration dictionary.

        Each key is the server name, each value a dict with at least
        a ``type`` key (``"stdio"`` or ``"http"``) plus constructor
        parameters for the corresponding class.

        Args:
            config: Mapping of server name → server configuration dict.

        Returns:
            Populated :class:`MCPServerRegistry`.

        Raises:
            ValueError: If an unsupported server type is encountered.

        Example config::

            {
                "github": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "tool_prefix": "github",
                },
                "fetch": {
                    "type": "sse",
                    "url": "http://localhost:8080",
                },
            }
        """
        registry = cls()
        for name, raw_config in config.items():
            params = dict(raw_config)  # Defensive copy
            server_type = params.pop("type", None)

            if server_type == "stdio":
                server: MCPServer = MCPServerStdio(**params)
            elif server_type == "sse":
                server = MCPServerSSE(**params)
            elif server_type == "streamable_http":
                server = MCPServerStreamableHTTP(**params)
            else:
                msg = (
                    f"Unsupported MCP server type '{server_type}' for '{name}'. "
                    f"Supported: {', '.join(_SUPPORTED_TYPES)}"
                )
                raise ValueError(msg)

            registry.register(name, server)

        return registry
