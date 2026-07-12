---
name: r-architecture-standards
description: "Rules: Package structure, MCP server conventions, error handling, and configuration"
user-invocable: false
---

# Architecture Standards

Conventions that are **not obvious best practices**. If it's standard Python or general software engineering practice, it does not belong here unless OwlBear deviates from or adds specificity to the norm.

## Module Quality Vocabulary

Use these terms consistently when evaluating or designing code. A module is scale-agnostic: a
function, class, package, or tier-spanning slice can all be modules.

| Concept | Definition | Diagnostic |
|---------|------------|------------|
| **Module** | Something with an interface and an implementation | Name the responsibility it hides, not its file type or framework role. |
| **Interface** | Everything a caller must know to use a module correctly, including invariants, ordering, errors, configuration, and performance | If callers must understand internals, the effective interface is larger than its type signature. |
| **Implementation** | Behavior hidden inside a module | Internal composition does not need to become caller knowledge or an external seam. |
| **Depth** | Leverage delivered through the interface | Deep modules expose substantial behavior through a small interface; shallow modules make callers coordinate the behavior. |
| **Leverage** | Capability callers receive per unit of interface they must learn | One implementation pays back across multiple callers and tests. |
| **Locality** | Degree to which change, bugs, knowledge, and verification concentrate in one place | Good locality means a behavior change is understood and fixed once. |
| **Seam** | Location where behavior can vary without editing the caller | A seam is justified by real variation, usually at least two adapters. |
| **Adapter** | A concrete participant that satisfies an interface at a seam | It names the substitutable role, not a generic forwarding wrapper. |

### Deletion Test

Imagine deleting a module entirely. If deleting it removes only forwarding while callers become
simpler, it was shallow. If its hidden complexity reappears across callers, it was earning its keep.

Apply when evaluating new abstractions, adapters, and wrapper modules. A module that fails the Deletion Test is a candidate for removal or deepening (absorbing more responsibility behind a simpler interface).

### Interface Is the Test Surface

Callers and durable behavioral tests should cross the same interface. Tests may replace a dependency
below that interface, but should not bypass the behavior being claimed. If tests routinely need to
reach past the interface, reconsider the module shape before adding more test-only seams.

### Seam Discipline

- One adapter usually indicates a hypothetical seam; two adapters establish actual variation.
- A deep module may contain private internal seams without exposing them to callers.
- Prefer replacing a dependency below the tested interface over layering tests across every shallow
    internal module.

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
