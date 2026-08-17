# MCP Python SDK Deep-Dive

> **Owning task:** #2 — MCP Python SDK deep-dive
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

OwlBear v2 needs 3–4 custom MCP servers (kanban, knowledge, project) exposed to Copilot CLI agents via VS Code. This research covers the MCP Python SDK API surface, the three primitives, transport trade-offs, server lifecycle, VS Code registration, and practical patterns for building OwlBear's servers.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK README (v1 stable) | <https://github.com/modelcontextprotocol/python-sdk> | .95 |
| 2 | MCP Python SDK README.v2 (pre-alpha) | <https://github.com/modelcontextprotocol/python-sdk/blob/main/README.v2.md> | .90 |
| 3 | MCP Architecture Overview | <https://modelcontextprotocol.io/docs/concepts/architecture> | .85 |
| 4 | MCP Lifecycle Spec (2025-03-26) | <https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle> | .90 |
| 5 | VS Code MCP Server Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | .95 |

## 3. The Three Primitives

| Primitive | Control | Purpose | OwlBear Use |
|-----------|---------|---------|-------------|
| **Tools** | Model-controlled | Executable functions (side effects OK) | kanban ops, KB queries, project CRUD |
| **Resources** | App-controlled | Read-only context data | board state, project metadata, KB docs |
| **Prompts** | User-controlled | Reusable interaction templates | agent system prompts, task templates |

Each primitive has `*/list` (discovery) and `*/get` or `tools/call` (execution) methods. Listings are dynamic — servers can send `listChanged` notifications.

## 4. SDK API Surface (v1 stable vs v2 preview)

| Aspect | v1 (`FastMCP`) | v2 (`MCPServer`) |
|--------|---------------|-----------------|
| Import | `mcp.server.fastmcp.FastMCP` | `mcp.server.mcpserver.MCPServer` |
| Decorator API | `@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()` | Same |
| Context | `Context[ServerSession, LifespanT]` | `Context[LifespanT]` (simplified) |
| Server props | `ctx.fastmcp` | `ctx.mcp_server` |
| Transport opts | Settings object (`stateless_http`, `json_response`) | Passed to `.run()` / `.streamable_http_app()` |
| Low-level | `Server` with decorator handlers | `Server` with constructor callbacks |
| Structured output | Auto from return types | Same, default on |
| PyPI release | v1.26.0 (stable, Jan 2026) | Pre-alpha on `main`, Q1 2026 target |

**Recommendation (.80):** Use v1 (`FastMCP`) for initial implementation. v2 API is nearly identical; migration is a rename (`FastMCP` → `MCPServer`, `ctx.fastmcp` → `ctx.mcp_server`). v1 is production-stable today.

## 5. Transport Trade-offs

| Criterion | stdio | Streamable HTTP | SSE (legacy) |
|-----------|-------|-----------------|--------------|
| Latency | Lowest (no network) | HTTP overhead | HTTP + SSE overhead |
| Setup | Zero (process spawn) | Needs port/socket | Needs port |
| Multi-client | 1 client per process | Many clients | Many clients |
| VS Code support | Native (`type: "stdio"`) | Native (`type: "http"`) | Native (`type: "sse"`) |
| Error recovery | Client restarts process | HTTP reconnect | SSE reconnect |
| Sandbox (VS Code) | macOS/Linux only | N/A | N/A |
| KISS score | High | Medium | Low (superseded) |

**Recommendation (.90):** Use **stdio** for all OwlBear MCP servers. Rationale: (1) OwlBear is laptop-resident, single-user — no multi-client needed; (2) zero network config; (3) VS Code natively manages stdio process lifecycle (start/stop/restart); (4) aligns with KISS. Streamable HTTP is future option if remote access is needed.

## 6. Server Lifecycle

The MCP protocol defines three phases (Sources 3, 4):

1. **Initialization** — Client sends `initialize` with protocol version + capabilities. Server responds with its capabilities. Client sends `notifications/initialized`. Version and capability negotiation happens here.
2. **Operation** — Normal JSON-RPC 2.0 message exchange. Both sides respect negotiated capabilities.
3. **Shutdown** — For stdio: client closes stdin, waits, then SIGTERM, then SIGKILL. For HTTP: close connection.

**With FastMCP**, lifecycle is automatic:
- `mcp.run()` handles stdio/HTTP transport setup
- The `lifespan` async context manager handles startup/shutdown resources
- Error recovery: VS Code restarts crashed stdio servers automatically
- SDK cancels in-flight handlers when transport closes

Lifespan pattern for resource management:

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        await db.disconnect()


mcp = FastMCP("My Server", lifespan=app_lifespan)
```

## 7. VS Code Registration

Servers are registered in `.vscode/mcp.json` (workspace) or user profile:

```json
{
  "servers": {
    "owlbear-kanban": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}/../owlbear", "python", "-m", "packages.mcp_kanban"],
      "env": {}
    }
  }
}
```

Key points (Source 5):
- `type: "stdio"` — VS Code spawns and manages the process
- `command` + `args` define the executable
- `env` and `envFile` for configuration
- Dev mode: `"dev": {"watch": "packages/mcp_kanban/**/*.py"}` auto-restarts on changes
- VS Code provides IntelliSense in `mcp.json`

## 8. OwlBear Server Architecture (Recommended)

Per v2 decision (#1), OwlBear needs 3–4 MCP servers:

| Server | Package | Tools | Resources | Prompts |
|--------|---------|-------|-----------|---------|
| `mcp-kanban` | `packages/mcp-kanban/` | list, show, create, edit, move | board state, task details | — |
| `mcp-knowledge` | `packages/mcp-knowledge/` | search, ingest, refresh | doc summaries, graph stats | — |
| `mcp-project` | `packages/mcp-project/` | set-active, list-projects | project definition, config | — |

Each server: single `FastMCP` instance, stdio transport, `mcp.run()` entry point, minimal deps. The `lifespan` pattern manages shared resources (SQLite connections, kanban binary path).

## 9. Key Patterns for Implementation

1. **Decorator-based tools** — `@mcp.tool()` with type-annotated params; SDK auto-generates JSON Schema
2. **Context injection** — Add `ctx: Context` param for logging, progress, resource reads
3. **Structured output** — Return Pydantic models or TypedDicts; SDK validates automatically
4. **Lifespan** — `asynccontextmanager` yields shared resources (DB, config)
5. **Entry point** — `mcp.run()` for stdio, or `mcp.run(transport="streamable-http")` for HTTP

## 10. Follow-up Tasks

This research task tracks the required seed implementation tasks only: #14, #16, and #17.

1. #14 - Build mcp-kanban server.
  Priority rationale: `needed` because the kanban MCP boundary is required to decouple board operations from direct CLI usage.
  Dependencies: #2, #7.
  One-line AC: implement `packages/mcp-kanban/` with stdio MCP tools for list/show/create/edit/move plus `board://summary` resource.
  Created:

  ```powershell
  kanban\kanban-md.exe create "Build mcp-kanban server" --priority needed --status ideation --tags "phase-1,scope:mcp,type:build" --depends-on 2,7 --body "See docs/research/mcp-python-sdk.md section 10 for context. AC: implement packages/mcp-kanban with stdio MCP tools for list/show/create/edit/move plus board://summary resource."
  ```

  Created task ID after execution: #14.

2. #16 - Build mcp-knowledge server.
  Priority rationale: `needed` because agents require MCP access to the knowledge engine for search and ingest flows.
  Dependencies: #2, #34.
  One-line AC: implement `packages/mcp-knowledge/` with stdio MCP tools for search/ingest/source-list plus `knowledge://stats` resource.
  Created:

  ```powershell
  kanban\kanban-md.exe create "Build mcp-knowledge server" --priority needed --status ideation --tags "phase-1,scope:mcp,type:build" --depends-on 2,34 --body "See docs/research/mcp-python-sdk.md section 10 for context. AC: implement packages/mcp-knowledge with stdio MCP tools for search/ingest/source-list plus knowledge://stats resource."
  ```

  Created task ID after execution: #16.

3. #17 - Build mcp-project server.
  Priority rationale: `important` because project metadata and context resources are needed by downstream agent workflows.
  Dependencies: #2, #7.
  One-line AC: implement `packages/mcp-project/` with stdio MCP tools for project info/list plus project metadata resources.
  Created:

  ```powershell
  kanban\kanban-md.exe create "Build mcp-project server" --priority important --status ideation --tags "phase-1,scope:mcp,type:build" --depends-on 2,7 --body "See docs/research/mcp-python-sdk.md section 10 for context. AC: implement packages/mcp-project with stdio MCP tools for project info/list plus project metadata resources."
  ```

  Created task ID after execution: #17.
