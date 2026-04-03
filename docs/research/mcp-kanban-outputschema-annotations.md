# outputSchema + Tool Annotations for mcp-kanban

> **Owning task:** #477 — Switch move/pick to JSON output, remove board_context tool
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #477 was expanded with new ACs: define `outputSchema` for `move_task`/`pick_task` return values, return `structuredContent` alongside text content, and add `ToolAnnotations` to all tools in `server.py`. This research covers the new scope.

**Decisions:**

1. How does FastMCP generate `outputSchema` — what return type is needed?
2. What's the right error handling pattern when switching from `str` to structured return?
3. Which annotation hints apply to each kanban tool?
4. Do `start_work`/`end_work` (mentioned in AC) exist yet?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Spec 2025-11-25 — Tools | modelcontextprotocol.io/specification/2025-11-25/server/tools | 1.0 |
| 2 | MCP Python SDK v1.26.0 `mcp.types` | Installed: `.venv/Lib/site-packages/mcp/types.py` L1247-1375 | 1.0 |
| 3 | FastMCP `func_metadata.py` | `.venv/Lib/site-packages/mcp/server/fastmcp/utilities/func_metadata.py` L50-420 | 1.0 |
| 4 | FastMCP `server.py` `@tool()` decorator | `.venv/Lib/site-packages/mcp/server/fastmcp/server.py` L440-510 | .95 |
| 5 | mcp-knowledge server.py | `packages/mcp-knowledge/src/.../server.py` | .90 |
| 6 | mcp-knowledge annotation tests | `packages/mcp-knowledge/tests/test_ingest_graph_tools.py` L630-680 | .90 |

## 3. Analysis

### 3.1 outputSchema: How FastMCP Derives It

FastMCP auto-generates `outputSchema` from the function's **return type annotation**:

| Return type | Schema quality | `wrap_output` | Notes |
|-------------|---------------|---------------|-------|
| `BaseModel` subclass | Precise field-level schema | No | Best option |
| `TypedDict` | Precise field-level schema | No | Converted to Pydantic model |
| `dict[str, Any]` | `RootModel` wrapping — generic | No | Schema is just `{"type": "object"}` |
| `str` / `int` | Wrapped in `{"result": ...}` | Yes | Not useful for task objects |
| No annotation / `None` | No schema generated | — | Current state (returns `str`) |

**Verdict:** A Pydantic `BaseModel` return type produces the best outputSchema. Define a `KanbanTask(BaseModel)` matching the known JSON schema from `skills/kanban-md/references/json-schemas.md`.

### 3.2 Error Handling Change

Current pattern returns errors as normal strings (`"error: {msg}"`). With structured output, the return type is `KanbanTask`, so error strings can't be returned. Two options:

| Approach | Pros | Cons |
|----------|------|------|
| `raise ToolError(msg)` | MCP-correct (`isError: true`), LLMs can self-correct | Breaking: callers checking `error:` prefix |
| Return `CallToolResult` directly | Full control over content + structuredContent | Verbose, bypasses FastMCP validation |

**Recommendation:** `raise ToolError(msg)`. The `isError: true` flag is the MCP-specified error signaling mechanism. Current `"error: "` prefix convention is informal and undocumented at the protocol level. The SKILL.md error handling section needs updating regardless.

### 3.3 Tool Annotations Mapping

| Tool | `readOnlyHint` | `destructiveHint` | `idempotentHint` | Rationale |
|------|---------------|-------------------|------------------|-----------|
| `list_tasks` | `True` | — | `True` | Read-only query |
| `show_task` | `True` | — | `True` | Read-only lookup |
| `create_task` | — | `False` | — | Additive write, not destructive |
| `move_task` | — | `False` | `True` | Status update, idempotent |
| `edit_task` | — | `False` | — | `append_body` is not idempotent |
| `pick_task` | — | `False` | — | May claim/move (side effects vary by args) |

Notes: `—` means omit (use spec default). `destructiveHint` defaults to `True` in spec, so explicitly setting `False` for non-destructive writes is valuable.

### 3.4 start_work / end_work — Scope Mismatch

The AC mentions `start_work` and `end_work` tools, but they do **not** exist in `server.py` yet. They are planned by tasks #470 and #471. Annotations for those tools should be added when they are implemented, not in #477.

### 3.5 Implementation Approach

**KanbanTask model** (~20 LOC):

```python
class KanbanTask(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    created: str  # ISO timestamp
    updated: str
    # omitempty fields
    started: str | None = None
    completed: str | None = None
    assignee: str | None = None
    tags: list[str] = []
    due: str | None = None
    estimate: str | None = None
    parent: int | None = None
    depends_on: list[int] = []
    blocked: bool = False
    block_reason: str | None = None
    body: str | None = None
    file: str | None = None
```

**Tool change pattern** (per tool):

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def show_task(ctx: Context, task_id: str) -> KanbanTask:
    ...
    if rc != 0:
        raise ToolError(stderr.strip())
    return KanbanTask.model_validate_json(stdout)
```

FastMCP auto-generates outputSchema from `KanbanTask` return type and produces both `content` (text) and `structuredContent` (dict) in the response.

## 4. Recommendation (.90 confidence)

1. **Define `KanbanTask` Pydantic model** in `packages/mcp-kanban/src/owlbear_mcp_kanban/models.py`
2. **Add `ToolAnnotations`** to all 6 tools per the mapping in 3.3 — independent of outputSchema
3. **Add outputSchema** to `show_task`, `move_task`, `pick_task` (after --json switch from #489) by changing return type to `KanbanTask`
4. **Switch error handling** from `return "error: ..."` to `raise ToolError(...)` for tools with structured output
5. **Defer start_work/end_work annotations** — those tools don't exist yet

Risk: The `ToolError` switch is a behavioral change for callers relying on `error:` prefix. Low risk since callers are LLM agents, not programmatic clients.

## 5. Follow-up Tasks

See task body for `kanban-md create` commands.
