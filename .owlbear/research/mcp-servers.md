# MCP Servers — Inventory, Evaluation, Integration Path

> **Owning task:** #137 — MCP servers — inventory, evaluation, integration path
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs to decide whether and how to integrate MCP (Model Context Protocol) servers alongside its native `FunctionToolset` subclasses. MCP is an open standard (Anthropic, now LF Projects) providing a standardized interface ("USB-C for AI") for connecting AI applications to external tools, data, and workflows. PydanticAI v1.63.0 has first-class MCP client support where `MCPServer` extends `AbstractToolset` — the same base class our `FunctionToolset` uses — enabling zero-friction integration with `Agent(toolsets=[...])`.

**Research questions answered:**

1. What is MCP and what servers exist? (§2, §3)
2. How does PydanticAI integrate MCP? (§3.1)
3. Which servers overlap with native OwlBear toolsets? (§3.2)
4. Which servers add new capabilities? (§3.2)
5. Does VS Code provide MCP servers we can reuse? (§3.3)
6. How do authentication and secrets work? (§3.4)
7. What is the minimal integration path? (§4, §5)

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| MCP Introduction | <https://modelcontextprotocol.io/introduction> | .95 | Protocol spec, transport types, architecture |
| MCP Servers repo | <https://github.com/modelcontextprotocol/servers> | .95 | Reference + community server inventory |
| PydanticAI MCP Client docs | <https://ai.pydantic.dev/mcp/client/> | .95 | MCPServerStdio/SSE/StreamableHTTP usage, load_mcp_servers(), tool_prefix, process_tool_call |
| PydanticAI MCP API reference | <https://ai.pydantic.dev/api/mcp/> | .90 | Full MCPServer class API, MCPServerConfig, ServerCapabilities |
| OwlBear codebase (agent.py, agent_registry.py, tools/) | (local) | 1.0 | Current toolset architecture, integration points |
| PydanticAI multi-agent research (task #127) | docs/research/pydantic-ai-multi-agent.md | .80 | Prior P8 research noting MCP as "Future P10" |

## 3. Analysis

### 3.1 PydanticAI MCP Integration Model

PydanticAI provides three client classes, all extending `AbstractToolset`:

| Class | Transport | Use case | Startup |
|-------|-----------|----------|---------|
| `MCPServerStdio` | stdio (subprocess) | Local CLI servers (npx, uvx) | Auto-start subprocess |
| `MCPServerStreamableHTTP` | Streamable HTTP | Remote/long-running servers | Must be running |
| `MCPServerSSE` | HTTP+SSE (deprecated) | Legacy servers | Must be running |

Key APIs: `load_mcp_servers(config_path)` loads from JSON config; `tool_prefix` avoids naming conflicts; `process_tool_call` hooks enable metadata injection; `MCPServer.__aenter__/__aexit__` manages lifecycle as async context manager. Because `MCPServer` extends `AbstractToolset`, it integrates with `HookedToolset`, `FilteredToolset`, and `RolePolicy` with zero adapter code.

### 3.2 Server Evaluation Matrix

| Server | Package | Runtime | Overlaps Native? | Value Add | Deps | KISS | Rec |
|--------|---------|---------|-------------------|-----------|------|------|-----|
| **GitHub** | `@modelcontextprotocol/server-github` | npx | No | High — repos, issues, PRs, search, code search | Node.js + PAT | High | **.90 Adopt** |
| **Git** | `@modelcontextprotocol/server-git` | npx/uvx | Partial (terminal) | Medium — structured status, diff, log, commit | Node.js or Python | High | **.80 Consider** |
| **Fetch** | `@modelcontextprotocol/server-fetch` | npx/uvx | No | Medium — URL fetch with HTML→Markdown | Node.js or Python | High | **.75 Consider** |
| **Brave Search** | `@modelcontextprotocol/server-brave-search` | npx | No | Medium — web search | Node.js + API key | Med | **.70 Defer** |
| Filesystem | `@modelcontextprotocol/server-filesystem` | npx | **Yes** (FileToolset) | Low — generic vs sandboxed | Node.js | Low | **.20 Skip** |
| Memory | `@modelcontextprotocol/server-memory` | npx | **Yes** (knowledge graph) | Low — flat KG vs sqlite-vec | Node.js | Low | **.15 Skip** |
| Playwright | `@playwright/mcp` | npx | **Yes** (BrowserToolset) | Medium — more tools | Node.js + migration risk | Low | **.30 Skip now** |
| Seq. Thinking | `@modelcontextprotocol/server-sequential-thinking` | npx | No | Low — achievable via prompts | Node.js | Med | **.25 Skip** |

**Rationale for skips:** FileToolset is sandboxed to `workspace_root` with OwlBear-specific safety rules — the generic MCP filesystem server lacks these. Our knowledge graph (sqlite-vec + fastembed) is far more capable than Memory's flat entity-relation store. BrowserToolset has deep integration with our `CommandGuard` and hook system — migrating to Playwright MCP would lose these safety features without clear upside.

### 3.3 VS Code MCP Support

VS Code supports MCP servers via `.vscode/mcp.json` for Copilot Chat. This is **separate from OwlBear** — VS Code's MCP config feeds its own Copilot Chat agent, not external processes. However, if OwlBear also uses JSON config for MCP servers, the team could share server definitions between VS Code and OwlBear by copying the `mcpServers` block. PydanticAI's `load_mcp_servers()` uses the same JSON schema as VS Code/Claude Code (`{"mcpServers": {...}}`), making config portable.

### 3.4 Authentication and Secrets

MCP servers receive credentials via environment variables passed to `MCPServerStdio(env={...})`:

| Server | Required Env Var | Source |
|--------|-----------------|--------|
| GitHub | `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub PAT (could reuse Copilot OAuth token) |
| Brave Search | `BRAVE_API_KEY` | Brave Search API subscription |
| Others | None | Local-only, no auth needed |

`load_mcp_servers()` supports `${VAR}` and `${VAR:-default}` expansion in config files. OwlBear's `pydantic-settings` config can inject these from `.env` or environment.

### 3.5 Integration Architecture

Current flow: `AgentDefinition.tools: list[str]` → `AgentRegistry._tool_resolver(name)` → `FunctionToolset` instance → `Agent(toolsets=[...])`.

Proposed extension: tool names prefixed with `mcp:` (e.g., `mcp:github`) resolve to `MCPServer` instances from a registry of configured MCP servers. Since `MCPServer` extends `AbstractToolset`, no changes needed to `OwlBearAgent`, `HookedToolset`, or `RolePolicy`.

```
AgentDefinition.tools = ["filesystem", "terminal", "mcp:github"]
                                                        ↓
                              MCPServerRegistry.get("github")
                                                        ↓
                              MCPServerStdio("npx", ["-y", "@modelcontextprotocol/server-github"],
                                             env={"GITHUB_PERSONAL_ACCESS_TOKEN": ...},
                                             tool_prefix="github")
```

## 4. Recommendation (.85 confidence)

**Adopt a hybrid model:** keep native toolsets for OwlBear-specific tools (filesystem, terminal, browser, ask_user, delegation) and add MCP servers for **new capabilities** that OwlBear doesn't have.

**Phase 1 — GitHub MCP server** (.90 confidence): Highest value, no native overlap, directly useful for the development workflow (issue tracking, PR creation, code search). Requires only a GitHub PAT.

**Phase 2 — Git + Fetch** (.80 confidence): Git provides structured access replacing ad-hoc terminal commands. Fetch enables web content retrieval for research tasks.

**Phase 3 — Brave Search** (.70 confidence): Adds web search but requires paid API key. Defer until web search is explicitly needed.

**Do not replace native toolsets with MCP equivalents.** Our FileToolset, BrowserToolset, and knowledge graph are more capable, safer, and better integrated than their MCP counterparts.

## 5. Follow-up Tasks

1. **MCP client infrastructure** — Add `pydantic-ai[mcp]` dependency, create `MCPServerRegistry` class, extend `AgentRegistry._tool_resolver()` to handle `mcp:` prefix, add MCP config section to settings
2. **GitHub MCP server integration** — Configure `@modelcontextprotocol/server-github`, wire through `MCPServerStdio`, add `mcp:github` as tool in agent definitions, test with PAT
3. **Git MCP server integration** — Configure `@modelcontextprotocol/server-git`, wire through `MCPServerStdio`, add `mcp:git` as tool
4. **Fetch MCP server integration** — Configure `@modelcontextprotocol/server-fetch`, wire through `MCPServerStdio`, add `mcp:fetch` as tool
5. **MCP server lifecycle management** — Implement `async with` server lifecycle in `OwlBearAgent.run()`, handle subprocess cleanup, add health checks
