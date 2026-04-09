---
name: r-architecture-standards
description: "Rules: Package structure, MCP server conventions, error handling, and configuration"
user-invocable: false
---

# Architecture Standards

Conventions that are **not obvious best practices**. If it's standard Python or general software engineering practice, it does not belong here unless OwlBear deviates from or adds specificity to the norm.

## v2 Architecture Overview

OwlBear v2 has no custom Python agent runtime. Agents are `.agent.md` files dispatched by the orchestrator via ACP (Copilot CLI). Tools are provided by MCP servers (`serve/mcp-*`) or VS Code built-in tools.

```
serve/orchestrator/       (ACP client, dispatch planning, CLI entry point)
    dispatches via ACP to
agents/*.agent.md            (agent definitions — pure markdown, no Python)
    use tools from
serve/mcp-kanban/         (MCP server: kanban board operations)
serve/mcp-knowledge/      (MCP server: knowledge base operations)
serve/mcp-project/        (MCP server: project metadata)
serve/mcp-memory/         (MCP server: persistent agent memory)
    import from
serve/knowledge/          (core library: graph, vector, ingest, query)
```

Each MCP server is a standalone FastMCP application. Core libraries live in separate packages. Cross-package imports are enforced by `tests/test_package_boundary.py`.

## MCP Server Conventions

All custom MCP servers (`mcp-kanban`, `mcp-knowledge`, `mcp-project`, `mcp-memory`) follow these conventions:

### Error Handling

- **`error:` string prefix** (`isError=false`): use for `str`-return and union-return tools (`TypedDict | str`). Error strings start with `error:` (e.g., `f"error: {stderr.strip()}"`).
- **`ToolError` exception** (`isError=true`): use when the return type is a pure model (TypedDict, BaseModel, or list thereof) and an error string cannot be embedded in the typed return.
- Both approaches are MCP-spec-valid; the spec distinguishes protocol errors from tool execution errors.
- Empty-result messages (e.g., "No sources found.") are informational — no prefix.
- MCP tools catch specific exceptions, never bare `except Exception`.
- Never expose raw tracebacks, tokens, or internal paths in tool responses.

#### Anti-pattern: double-prefix

**Never** pass an `"error: "` prefix in the message string to `ToolError`. The MCP transport already marks the response `isError: true` — the prefix is redundant and creates duplicate `"error: error: ..."` rendering in clients.

```python
# WRONG — double-prefix anti-pattern
raise ToolError("error: source store not available")

# CORRECT — bare message
raise ToolError("source store not available")
```

This applies to all `ToolError` calls regardless of context. The same `"error: "` prefix rule still applies to soft-error *return strings* from `str`-return tools.

### Tool Annotations

Every tool declares three annotation fields in its `ToolAnnotations`:

| Annotation | Type | Purpose |
|-----------|------|---------|
| `readOnlyHint` | bool | Tool does not modify state |
| `idempotentHint` | bool | Repeated calls with same args have same effect |
| `destructiveHint` | bool | Tool can delete or irreversibly modify data |

See `mcp-kanban` for the reference implementation.

### Return Types

| Type | Use for |
|------|---------|
| `TypedDict` or `list[TypedDict]` | Structured queryable data (lists, metadata) — preferred for field-level outputSchema auto-generation |
| `BaseModel` subclasses | Complex entities with validation |
| `str` | Content bodies, messages, and errors |

### Lifespan Pattern

Server startup uses an `AppContext` dataclass and an `asynccontextmanager` lifespan function passed to `FastMCP`:

```python
@dataclass
class AppContext:
    kanban_bin: Path
    # ... server-specific fields

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    ctx = AppContext(kanban_bin=resolve_binary())
    yield ctx
```

### Tool Exclusion

Each server reads a `*_TOOLS_EXCLUDE` env var at startup:

| Server | Env var |
|--------|---------|
| mcp-kanban | `KANBAN_TOOLS_EXCLUDE` |
| mcp-knowledge | `KNOWLEDGE_TOOLS_EXCLUDE` |
| mcp-project | `PROJECT_TOOLS_EXCLUDE` |
| mcp-memory | `MEMORY_TOOLS_EXCLUDE` |

Comma-separated tool names are removed via `server.remove_tool()`. Unknown names are silently ignored. Default (unset) = all tools registered.

### Module Exports

Every `server.py` defines `__all__` listing its public symbols.

## Package Dependency Rules

Cross-namespace imports are enforced by `tests/test_package_boundary.py`. The `ALLOWED_IMPORTS` constant in that file maps each package namespace to its permitted owlbear-namespace imports.

**Rules:**

- When adding a new package, update `ALLOWED_IMPORTS` — the manifest guard will fail otherwise.
- TYPE_CHECKING import policy is documented in the test module docstring.
- MCP servers may import from their corresponding core library (e.g., `mcp-knowledge` imports from `knowledge`) but not from other MCP servers.

## Configuration

- MCP servers read configuration from environment variables at startup (see each server's handbook skill for the variable list: `h-mcp-kanban`, `h-mcp-project`, `h-knowledge-ops`).
- Core library settings use `pydantic-settings` fields. Never read `os.environ` directly in library code — surface it through the MCP server's `AppContext`.
- Feature flags use `bool` fields with `default=False` (opt-in).

## Domain Taxonomy

Each task targets exactly one domain. Multi-domain work must be split into separate tasks.

| Domain | Scope |
|--------|-------|
| orchestrator | `serve/orchestrator/` (ACP client, dispatch, CLI, analysis) |
| knowledge | `serve/knowledge/` (graph, vector, ingest, query, embeddings) |
| mcp-kanban | `serve/mcp-kanban/` |
| mcp-knowledge | `serve/mcp-knowledge/` |
| mcp-project | `serve/mcp-project/` |
| mcp-memory | `serve/mcp-memory/` |
| voice | `serve/voice/` |
| agent-config | `agents/`, `skills/`, `instructions/`, `.github/copilot-instructions.md` |
| test-infra | shared conftest, fixtures, factories (not individual test files) |
| docs | `docs/`, `README.md`, `SECURITY.md` |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
