"""The C+ step's MCP relay (TD-36): the window's harness runs it; it forwards the step's tools to the runner.

``python -m owlbear_delivery_next step-mcp --inbox PATH``. The inbox names the runner's loopback receiver and its
token; without it, or once the step ended, the relay offers no tools and refuses every call.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

NOT_RUNNING = "No Delivery step is running in this folder any more. Stop now."
TIMEOUT = 60.0  # a result check reads the worktree with git
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy


def forward(inbox: Path, method: str, path: str, body: object = None) -> dict[str, Any] | None:
    """One request to the step's receiver; None when the inbox or the receiver is gone."""
    try:
        where = json.loads(inbox.read_text())
        url, token = f"{where['url']}{path}", where["token"]
    except OSError, ValueError, KeyError, TypeError:
        return None
    data = None if body is None else json.dumps(body).encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310 - loopback
    try:
        with _LOCAL.open(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            return json.load(exc)
        except ValueError:
            return None
    except urllib.error.URLError, OSError, ValueError:
        return None


def relay(inbox: Path) -> Server:
    """The MCP server that lists and forwards the step's tools."""

    async def list_tools(_ctx: object, _params: object) -> types.ListToolsResult:
        found = await anyio.to_thread.run_sync(forward, inbox, "GET", "/tools")
        listed = (found or {}).get("tools") or []
        return types.ListToolsResult(
            tools=[
                types.Tool(name=t["name"], description=t["description"], input_schema=t["inputSchema"]) for t in listed
            ]
        )

    async def call_tool(_ctx: object, params: types.CallToolRequestParams) -> types.CallToolResult:
        body = {"name": params.name, "arguments": params.arguments or {}}
        found = await anyio.to_thread.run_sync(forward, inbox, "POST", "/call", body)
        text, ok = (found["text"], bool(found.get("ok"))) if found and "text" in found else (NOT_RUNNING, False)
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=not ok)

    return Server("owlbear-step", on_list_tools=list_tools, on_call_tool=call_tool)


def main(argv: list[str] | None = None) -> None:
    """Serve the relay over stdio."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next step-mcp")
    parser.add_argument("--inbox", type=Path, required=True)
    server = relay(parser.parse_args(argv).inbox)

    async def serve() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(serve)
