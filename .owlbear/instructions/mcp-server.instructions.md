---
description: "OwlBear MCP server conventions — errors, tool contracts, lifespan, exports, and configuration"
applyTo: "serve/mcp-*/**"
---

## Error Handling

- Use an `error:` string prefix for soft-error return strings when the return type permits text.
- Raise `ToolError` with a bare message when a typed return cannot embed an error string. Never pass
  an `error:` prefix to `ToolError`; the transport already marks the result as an error.
- Empty-result messages are informational and have no `error:` prefix.
- Catch specific exceptions. Never expose raw tracebacks, tokens, or internal paths in responses.

## Tool Contracts

- Every tool declares `readOnlyHint`, `idempotentHint`, and `destructiveHint` annotations.
- Prefer `TypedDict` or `list[TypedDict]` for structured queryable projections, Pydantic models for
  complex validated entities, and `str` for content bodies or soft-error messages.
- Use the relevant existing MCP package as the nearest implementation precedent; do not introduce a
  new cross-server convention from one isolated tool.

## Lifespan and Configuration

- Server startup uses an `AppContext` dataclass and an `asynccontextmanager` lifespan passed to
  `FastMCP`.
- Read environment configuration at server startup and place resolved dependencies in `AppContext`.
  Core libraries receive explicit settings or dependencies rather than reading `os.environ`.
- Feature flags are opt-in boolean settings with `default=False` unless product requirements state
  otherwise.
- Tool exclusion is server-specific. Use the server's documented environment variable and
  `server.remove_tool()` behavior; do not assume every server supports exclusions.

## Public Surface

- Every `server.py` defines `__all__` for its public symbols.
- MCP-facing return types and error semantics are public contracts. Update callers and focused
  contract tests when they change.
