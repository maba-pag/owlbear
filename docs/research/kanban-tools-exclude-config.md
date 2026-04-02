# KANBAN_TOOLS_EXCLUDE Configuration for Selective Tool Exposure

> **Owning task:** #473 — Add KANBAN_TOOLS_EXCLUDE config for selective tool exposure
> **Date:** 2026-03-31 **Status:** Complete (revised)

## 1. Context and Question

The mcp-kanban server registers all 8 tools (`list_tasks`, `show_task`, `create_task`,
`move_task`, `edit_task`, `pick_task`, `start_work`, `end_work`) unconditionally. Some deployments
may want to restrict which tools are available — e.g., a read-only setup that excludes
mutation tools, or a consumer project that doesn't need `pick_task`.

**Question:** How should the server filter tools at startup based on configuration?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | FastMCP v1.26.0 `server.py` | Installed: `.venv/Lib/site-packages/mcp/server/fastmcp/server.py` | `.95` — confirmed public `remove_tool(name) -> None`, raises `ToolError` on unknown |
| 2 | FastMCP `tool_manager.py` | Installed: `.venv/Lib/site-packages/mcp/server/fastmcp/tools/tool_manager.py` | `.90` — `remove_tool` delegates here, raises `ToolError` |
| 3 | OwlBear mcp-kanban server | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | `.95` — `KANBAN_BIN` env var read in lifespan (not module level), tool registration via decorators |

## 3. Analysis

### 3.1 Implementation Approaches

| Criterion | A: Module-level removal (.65) | B: Lifespan removal (.85) | C: Conditional decorator (.50) |
|-----------|-------------------------------|---------------------------|-------------------------------|
| Complexity | ~15 LOC helper | ~15 LOC helper + 1 line in lifespan | Wrapper around `@mcp.tool()` |
| KISS | Medium — import-time surprise | High — natural startup config | Low — changes registration flow |
| Testability | Must set env var before import | Helper is sync, call directly | Complex mock setup |
| Side effects | Runs at import time (fragile) | Runs at server startup (correct) | Changes decoration semantics |
| API used | `mcp.remove_tool(name)` | `_server.remove_tool(name)` | Skip decorator entirely |
| Existing pattern | No precedent — `KANBAN_BIN` is read in lifespan | Matches `KANBAN_BIN` env read in `app_lifespan` | No precedent |
| Ordering safety | Fragile — must be placed after all decorators | Robust — all decorators run before lifespan | N/A |

**Correction from prior analysis:** `KANBAN_BIN` is read inside `app_lifespan()`,
not at module level. Option B follows this existing pattern; Option A does not.

### 3.2 FastMCP `remove_tool` API (verified locally)

MCP SDK v1.26.0: `FastMCP.remove_tool(name: str) -> None` delegates to
`_tool_manager.remove_tool(name)`. Raises `ToolError` if the tool does not exist.
Confirmed via local introspection — this is the stable public API.

### 3.3 Env Var Design

`KANBAN_` prefix convention established by `KANBAN_BIN`. `KANBAN_TOOLS_EXCLUDE` follows
this. Comma-separated is unambiguous for tool names (no commas in tool identifiers).

### 3.4 mcp.json Integration

```json
"owlbear-kanban": {
  "type": "stdio",
  "command": "uv",
  "args": ["run", "python", "-m", "owlbear_mcp_kanban"],
  "env": { "KANBAN_TOOLS_EXCLUDE": "create_task,edit_task,move_task" }
}
```

## 4. Recommendation (.85 confidence)

**Option B: Lifespan removal using `_server.remove_tool()` inside `app_lifespan`.**

The lifespan already receives `_server: FastMCP` and reads `KANBAN_BIN` from env.
Adding tool exclusion here follows the established pattern and avoids import-time
side effects.

Implementation sketch:

```python
def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Remove tools listed in KANBAN_TOOLS_EXCLUDE env var (comma-separated)."""
    exclude_csv = os.environ.get("KANBAN_TOOLS_EXCLUDE", "")
    if not exclude_csv:
        return set()
    excluded: set[str] = set()
    for name in exclude_csv.split(","):
        name = name.strip()
        if not name:
            continue
        try:
            server.remove_tool(name)
            excluded.add(name)
        except Exception:  # noqa: BLE001 — silently ignore invalid names
            pass
    return excluded
```

Called in `app_lifespan` before `yield`:

```python
@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    # ... existing binary discovery ...
    _apply_tool_exclusions(_server)
    yield AppContext(kanban_bin=kanban_bin, kanban_dir=_DEFAULT_KANBAN_DIR)
```

**Why not Option A (module-level)?** `KANBAN_BIN` is read in the lifespan, not at
module level. Module-level removal creates an import-time side effect and ordering
fragility (must follow all `@mcp.tool()` decorators). The lifespan naturally runs after
all decorators and before any client interaction.

**Risks:**
- `remove_tool` raises on unknown names — mitigated by try/except per AC requirement.
- No risk of timing issues: lifespan runs after all decorators but before tool listing.

## 5. Follow-up Tasks

Implementation task #491 created at `ideation` (see task body for AC).
Research doc updated 2026-03-31 with corrected analysis (Option B over A).
