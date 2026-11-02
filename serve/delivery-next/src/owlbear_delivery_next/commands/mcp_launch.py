"""OwlBear's other chat servers, run from the installed version (D-01M5Q5GKHX7BJTXPEW2MHGS9E0, "move all").

``python -m owlbear_delivery_next serve memory`` (or ``knowledge``, ``browser``) runs that package's MCP server in
this process. The dispatcher has pinned it to its version's own folder and taken a lease first, so a chat keeps the
server it started with while OwlBear updates beneath it, and no update removes that code. The servers are named,
not imported: Delivery depends on none of them. Their working folder and environment are the client's.

Every server here, the chat server too, serves only the 2025 ``initialize`` handshake (``serve_stdio``): the ``mcp``
library's own stdio runner lets a client's first request pick the 2026-07-28 era and then refuses ``initialize``,
which is the fallback the Copilot CLI sends after its ``server/discover`` (#906).
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import TYPE_CHECKING

import anyio
from mcp.server.runner import serve_loop
from mcp.server.stdio import stdio_server

if TYPE_CHECKING:
    from mcp.server import MCPServer

SERVERS = {"memory": "owlbear_memory_mcp", "knowledge": "owlbear_knowledge_mcp", "browser": "owlbear_browser_mcp"}
USAGE = f"usage: python -m owlbear_delivery_next serve {{{','.join(SERVERS)}}}"


def main(argv: list[str]) -> int:
    """Run the named server until its client ends it; 2 for a wrong name, or a server this install lacks."""
    if argv == ["--help"]:
        print(USAGE)  # noqa: T201 - asked for; no client reads it
        return 0
    if len(argv) != 1 or argv[0] not in SERVERS:
        print(f"{USAGE}: {' '.join(argv) or 'no server'} is not one", file=sys.stderr)  # noqa: T201
        return 2
    module = SERVERS[argv[0]]
    if importlib.util.find_spec(module) is None:
        lacking = f"{module} is not installed in {sys.prefix}: this OwlBear install is incomplete"
        print(lacking, file=sys.stderr)  # noqa: T201
        return 2
    sys.argv = [sys.argv[0]]  # the servers read no arguments
    serve_stdio(importlib.import_module(f"{module}.server").mcp)  # an import error inside it is its own, raised
    return 0


def serve_stdio(server: MCPServer) -> None:
    """Serve *server* over stdio in the 2025 handshake era only, until the client closes its input.

    As ``MCPServer.run`` does, but through ``serve_loop``: a request before ``initialize`` gets an error, ``ping``
    excepted, so a client that opens with ``server/discover`` falls back to ``initialize`` and is served.
    """
    low = server._lowlevel_server  # noqa: SLF001 - the library offers no other way to its lifespan and handlers

    async def run() -> None:
        async with stdio_server() as (read, write), low.lifespan(low) as state:
            await serve_loop(low, read, write, lifespan_state=state, init_options=low.create_initialization_options())

    anyio.run(run)
