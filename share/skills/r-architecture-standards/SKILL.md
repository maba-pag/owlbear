---
name: r-architecture-standards
description: "Rules: Package structure, MCP server conventions, error handling, and configuration"
user-invocable: false
---

# Architecture Standards

Conventions that are **not obvious best practices**. If it's standard Python or general software engineering practice, it does not belong here unless OwlBear deviates from or adds specificity to the norm.

## Module Quality Vocabulary

Shared terminology for evaluating module quality across the pipeline (derived from Ousterhout's *A Philosophy of Software Design*).

| Concept       | Definition                                                  | Diagnostic                                                                           |
| ------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Depth**     | Ratio of implementation complexity to interface complexity   | Deep modules do a lot behind a simple interface. Shallow modules expose everything.  |
| **Leverage**  | How many callers benefit from a module                      | High leverage = change once, benefit everywhere.                                     |
| **Locality**  | How much context you need to understand a change            | Good locality = changes are contained within one module boundary.                    |
| **Seam**      | A boundary where you can substitute implementations         | Real seam: 2+ implementations. Hypothetical seam: 1 adapter = speculative.           |
| **Adapter**   | Translates between two interfaces at a seam                 | One adapter = hypothetical seam. Two adapters = real seam earning its keep.           |

### Deletion Test

Imagine deleting a module entirely. If the complexity it managed **vanishes** (callers become simpler), the module was a pure pass-through — inline it or delete it. If the complexity **reappears across N callers**, the module is earning its keep.

Apply when evaluating new abstractions, adapters, and wrapper modules. A module that fails the Deletion Test is a candidate for removal or deepening (absorbing more responsibility behind a simpler interface).

### Dependency Classification

| Type                       | Example                      | Seam needed? |
| -------------------------- | ---------------------------- | ------------ |
| In-process                 | Direct function call          | Rarely       |
| Local-substitutable        | File-system adapter           | Maybe        |
| Remote-but-owned           | Our MCP server                | Yes          |
| True-external              | Third-party API               | Yes          |

## MCP Server Conventions

All custom MCP servers (`mcp-kanban`, `mcp-knowledge`, `mcp-memory`) follow these conventions:

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
    engine: KanbanEngine
    kanban_dir: Path
    # ... server-specific fields

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    engine = KanbanEngine(kanban_dir)
    yield AppContext(engine=engine, kanban_dir=kanban_dir)
```

### Tool Exclusion

Tool exclusion is supported on select servers only:

| Server | Env var |
|--------|---------|
| mcp-knowledge | `KNOWLEDGE_TOOLS_EXCLUDE` |

Comma-separated tool names are removed via `server.remove_tool()`. Unknown names are silently ignored. Default (unset) = all tools registered.

### Module Exports

Every `server.py` defines `__all__` listing its public symbols.

## Configuration

- MCP servers read configuration from environment variables at startup (see each server's handbook skill for the variable list: `h-mcp-kanban`, `h-knowledge-ops`).
- Core library settings use `pydantic-settings` fields. Never read `os.environ` directly in library code — surface it through the MCP server's `AppContext`.
- Feature flags use `bool` fields with `default=False` (opt-in).
