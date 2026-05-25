# assess_memories MCP Tool — Implementation Research

> **Owning task:** #1846 — P2-07: assess_memories MCP tool
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Task #1846 adds an `assess_memories` MCP tool to `serve/mcp-memory/` that accepts batch assessments from agents at end-of-task. Dependencies #1841 (model fields/score), #1844 (slot-efficiency), #1845 (confirmation cycle) are all archived/complete. The engine already exposes `compute_score`, `check_slot_efficiency`, `try_stale_transition`, and `record_factually_wrong`. The gap: no public engine method to atomically increment a counter + recompute score.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | FastMCP tools documentation (gofastmcp.com/servers/tools) | 0.9 — confirms list[TypedDict], enum inputs, ToolError pattern |
| 2 | mcp-batchit (github.com/ryanjoachim/mcp-batchit) | 0.7 — batch pattern: per-item {success, error} with stopOnError |
| 3 | Existing `tools.py` / `server.py` / `engine.py` in serve/mcp-memory | 1.0 — establishes local conventions |
| 4 | REST bulk API partial success patterns (oneuptime.com) | 0.6 — HTTP 207 Multi-Status equivalent for per-item results |

## 3. Analysis

### 3.1 Implementation Approach

| Layer | Change | LOC est. |
|-------|--------|----------|
| `owlbear_memory/engine.py` | New `record_assessment(entry_id, bucket, expected_updated_at)` method | ~25 |
| `owlbear_mcp_memory/tools.py` | New `assess_memories()` orchestrator function | ~55 |
| `owlbear_mcp_memory/server.py` | `@mcp.tool` registration + import | ~20 |
| `owlbear_memory/models.py` (or engine) | `AssessmentBucket` StrEnum (4 values) | ~8 |

### 3.2 Key Design Decisions (Trade-off Matrix)

| Decision | Option A | Option B | Chosen |
|----------|----------|----------|--------|
| Engine method granularity | Single `record_assessment` (validates + increments + recomputes + writes) | Three separate `increment_X` methods | A — matches existing patterns (approve, edit, delete are self-contained) |
| OCC for counter writes | Include optional `expected_updated_at` CAS guard | Skip OCC (single-user assumption) | A — matches `record_factually_wrong` pattern, no lost increments on concurrent sessions |
| Bucket validation location | Engine validates (raises `ValidationError`), tool converts to `ToolError` | Tool-only validation | A — consistent with engine owning domain rules |
| Invalid bucket semantics | ToolError aborts entire batch (schema-level error) | Per-item failure | A — AC1 says "raises ToolError"; distinct from AC3 entry-level failures |
| Input type | TypedDict `Assessment = {entry_id: str, bucket: str}` | Raw `list[dict[str, str]]` | TypedDict — better JSON schema generation by FastMCP |
| Duplicate entry_ids | Allowed, sequential deterministic semantics | Reject duplicates | Allow — AC doesn't prohibit; sequential processing is deterministic |
| factually_wrong path | Only `record_factually_wrong` (no counter/score/stale) | Also run slot-efficiency check | Only record_factually_wrong — factually_wrong has no counter to increment |

### 3.3 Challenger Adjustments

Challenger identified 5 concerns (confidence in original: 0.46). Resolutions:

1. **OCC**: Added. Engine method takes optional `expected_updated_at`. Tool passes fresh `entry.updated_at`.
2. **factually_wrong stale**: AC2 reads as two paths — counter-increment path (outstanding/unremarkable/didnt_use) triggers slot-efficiency, factually_wrong path only calls `record_factually_wrong`. No counter exists for factually_wrong.
3. **Batch abort**: Treated as schema vs. domain error split. Invalid bucket = schema error (ToolError aborts). Non-existent/non-voteable = domain error (per-item failure).
4. **Duplicate entry_ids**: Allowed. Sequential processing gives deterministic semantics.
5. **Engine validation**: Engine validates bucket via `AssessmentBucket` StrEnum (raises `ValidationError`). Tool converts at boundary.

## 4. Recommendation

**Proceed with implementation** using the single `record_assessment` engine method + thin tool orchestrator approach.

Challenge: proceed — confidence in original after adjustments: 0.82

### Tool Signature (draft)

```python
# tools.py
async def assess_memories(
    ctx: Context,
    *,
    assessments: list[Assessment],  # TypedDict: {entry_id: str, bucket: str}
    task_id: str,
) -> dict[str, Any]:
    """Process batch assessment submissions."""
```

### Engine Method (draft)

```python
# engine.py
def record_assessment(
    self, entry_id: str, bucket: AssessmentBucket,
    expected_updated_at: str | None = None,
) -> MemoryEntry:
    """Increment assessment counter, recompute score, persist."""
```

### Response Shape

```json
{
  "results": [
    {"entry_id": "...", "success": true},
    {"entry_id": "...", "success": false, "error": "entry not found: ..."}
  ]
}
```

## 5. Follow-up Tasks

Implementation decomposes naturally into this single task (#1846) with no additional research needed. All primitives are built. The task AC is sufficient for TDD.

Testing strategy: unit tests for `record_assessment` engine method + integration tests for MCP tool (batch processing, per-item failure, ToolError on invalid bucket, factually_wrong delegation, slot-efficiency trigger).
