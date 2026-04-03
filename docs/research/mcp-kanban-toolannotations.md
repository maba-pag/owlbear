# ToolAnnotations for mcp-kanban Tools

> **Owning task:** #494 — Add ToolAnnotations to all mcp-kanban tools
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Task #494 (follow-up from #477 research) requires adding `ToolAnnotations` metadata to all mcp-kanban tools. The annotations are MCP spec hints that help clients optimize tool invocation (e.g., skipping confirmation for read-only tools). The mcp-knowledge server already uses this pattern.

**Questions validated:**

1. Is the annotation mapping in the AC correct?
2. Are any tools missing from the AC?
3. What test pattern should be used?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | MCP Spec 2025-11-25 — Tools § annotations | 1.0 |
| 2 | MCP Python SDK v1.26.0 `mcp.types.ToolAnnotations` (L1247-1300) | 1.0 |
| 3 | mcp-knowledge `server.py` — existing annotation usage | .95 |
| 4 | mcp-knowledge `test_ingest_graph_tools.py` — annotation test pattern | .95 |
| 5 | Prior research: `docs/research/mcp-kanban-outputschema-annotations.md` (#477) | .90 |

## 3. Analysis

### 3.1 Annotation Mapping Validation

The AC's per-tool annotation mapping is correct. Verified against MCP spec defaults:

| Tool | `readOnlyHint` | `destructiveHint` | `idempotentHint` | Rationale |
|------|:-:|:-:|:-:|-----------|
| `list_tasks` | `True` | — | `True` | Read-only query, same filters = same result |
| `show_task` | `True` | — | `True` | Read-only lookup by ID |
| `board_context` | `True` | — | `True` | Read-only aggregate (missing from AC) |
| `create_task` | — | `False` | — | Additive write, not destructive |
| `move_task` | — | `False` | `True` | Status update is idempotent |
| `edit_task` | — | `False` | — | `append_body` makes it non-idempotent |
| `pick_task` | — | `False` | — | Side effects vary by args |

`—` = omit (use spec default). Spec defaults: `readOnlyHint=False`, `destructiveHint=True`, `idempotentHint=False`.

### 3.2 AC Gap: `board_context` Missing

The AC lists 6 tools but `server.py` registers 7 — `board_context` is omitted. It's a read-only aggregate query and should get `ToolAnnotations(readOnlyHint=True, idempotentHint=True)`.

### 3.3 `openWorldHint` Consideration

All kanban tools operate on local files (closed-world). Setting `openWorldHint=False` would be accurate. However, the spec default is `True` and the prior research didn't include it. Per KISS, omitting it is acceptable — it's a hint, not a behavioral change. Flagged for builder discretion.

### 3.4 Implementation Pattern

Copy the mcp-knowledge pattern — one-line change per tool:

```python
from mcp.types import ToolAnnotations

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_tasks(...) -> str:
```

### 3.5 Test Pattern

Copy `_get_tool_annotations()` helper from mcp-knowledge tests. One assertion per tool:

```python
def _get_tool_annotations(tool_name: str) -> object | None:
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None
```

## 4. Recommendation (.95 confidence)

**T1 — Autonomous.** No T3 triggers: no new capability, no architecture change, no pipeline/agent modification. This is decorator-level metadata following an established in-project pattern.

Proceed directly with implementation. Add `board_context` to the AC scope. The builder should add 7 `@mcp.tool(annotations=...)` decorators + 1 import + 7 test assertions.

Estimated diff: ~20 lines in `server.py`, ~40 lines in `test_server.py`.

## 5. Follow-up Tasks

No additional tasks needed — #494 already covers the full scope. The AC should be amended to include `board_context`.
