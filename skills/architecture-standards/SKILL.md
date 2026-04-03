---
name: architecture-standards
description: "OwlBear v2 architectural standards: package structure, MCP server conventions, error handling, configuration. Use when reviewing, building, or planning changes to packages/ code."
user-invocable: false
---

# Architecture Standards

This document lists only conventions that are **not obvious best practices**. If it's standard Python or general software engineering practice, it does not belong here unless OwlBear deviates from or adds specificity to the norm. When in doubt: if a senior Python developer would do it by default, don't list it.

## v2 architecture overview

OwlBear v2 has no custom Python agent runtime. Agents are `.agent.md` files dispatched by the orchestrator via ACP (Copilot CLI). Tools are provided by MCP servers (`packages/mcp-*`) or VS Code built-in tools.

```
packages/orchestrator/       (ACP client, dispatch planning, CLI entry point)
    ↓ dispatches via ACP
agents/*.agent.md            (agent definitions — pure markdown, no Python)
    ↓ use tools from
packages/mcp-kanban/         (MCP server: kanban board operations)
packages/mcp-knowledge/      (MCP server: knowledge base operations)
packages/mcp-project/        (MCP server: project metadata)
packages/mcp-memory/         (MCP server: persistent agent memory)
    ↓ import from
packages/knowledge/          (core library: graph, vector, ingest, query)
```

Each MCP server is a standalone FastMCP application. Core libraries live in separate packages (`packages/knowledge/`). Cross-package imports are enforced by `tests/test_package_boundary.py`.

## MCP server conventions

All custom MCP servers follow these patterns (see `.github/copilot-instructions.md` § MCP Server Conventions for the full list):

- **Error handling:** `ToolError` exception for typed returns, `error: ` string prefix for string/union returns.
- **Tool annotations:** Every tool declares `readOnlyHint`, `idempotentHint`, `destructiveHint`.
- **Return types:** `TypedDict` for structured data, `str` for content/messages.
- **Lifespan:** `AppContext` dataclass + `asynccontextmanager` lifespan passed to `FastMCP`.
- **Tool exclusion:** `*_TOOLS_EXCLUDE` env var per server.

## Error handling

- MCP tools catch specific exceptions, never bare `except Exception`.
- Error strings start with `error: ` prefix for string-return tools.
- `ToolError` for typed-return tools (sets `isError: true` in MCP response).
- Never expose raw tracebacks, tokens, or internal paths in tool responses.

## Configuration

- MCP servers read configuration from environment variables at startup (see each server's skill for the variable list).
- Core library settings use `pydantic-settings` fields. Never read `os.environ` directly in library code — surface it through the MCP server's `AppContext`.
- Feature flags use `bool` fields with `default=False` (opt-in).

## Domain taxonomy

Each task targets exactly one domain. Multi-domain work → split into separate tasks.

| Domain        | Scope                                                                |
| ------------- | -------------------------------------------------------------------- |
| orchestrator  | `packages/orchestrator/` (ACP client, dispatch, CLI, analysis)       |
| knowledge     | `packages/knowledge/` (graph, vector, ingest, query, embeddings)     |
| mcp-kanban    | `packages/mcp-kanban/`                                               |
| mcp-knowledge | `packages/mcp-knowledge/`                                            |
| mcp-project   | `packages/mcp-project/`                                              |
| mcp-memory    | `packages/mcp-memory/`                                               |
| voice         | `packages/voice/`                                                    |
| agent-config  | `agents/`, `skills/`, `instructions/`, `.github/copilot-instructions.md` |
| test-infra    | shared conftest, fixtures, factories (not individual test files)     |
| docs          | `docs/`, `README.md`, `SECURITY.md`                                  |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
