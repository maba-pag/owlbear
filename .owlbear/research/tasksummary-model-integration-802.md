# TaskSummary Model + Server Integration — Implementation Research

> **Owning task:** #802 — Add TaskSummary model + server integration
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #802 is the TDD GREEN phase for `TaskSummary`. The model must replace hand-built `_strip` dicts in `server.py` with a schema-validated Pydantic projection, and the engine `list_tasks` must return `list[TaskSummary]`. Question: what is the implementation approach, what patterns to follow, and what breaks?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/models.py` — current TaskSummary (lines 93-104) | 1.0 |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — `_strip` dict + `outputSchema` (lines 102-181) | 1.0 |
| S3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` — `KanbanTask._coerce_claimed` pattern (lines 32-38) | 0.9 |
| S4 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` — O2 outcome spec | 1.0 |
| S5 | `tests/test_kanban_engine_listing.py` — engine list_tasks tests (lines 183, 321) | 0.9 |
| S6 | `tests/test_kanban_mcp_migration.py` — MCP list_tasks tests (lines 210-295) | 0.9 |
| S7 | `.owlbear/research/tasksummary-model-tests-801.md` — #801 research | 0.8 |
| S8 | Pydantic v2 docs — `extra="ignore"`, `model_validator(mode="before")` | 0.8 |

## 3. Analysis

### 3.1 Model Changes (TaskSummary)

| Aspect | Current | Required | Approach |
|--------|---------|----------|----------|
| `extra` config | `"allow"` (leaks fields) | Exclude unwanted fields | `extra="ignore"` — silently drops extra fields from `Task.model_dump()` (S8) |
| `claimed_by` field | `str \| None` | Remove | Drop field; add `claimed: bool` |
| Missing fields | — | block_reason, claimed, parent, depends_on | Add with same types/defaults as `Task` model |
| `claimed_by` → `claimed` coercion | Not present | Bool from string | `@model_validator(mode="before")` — established pattern in `KanbanTask` (S3) |

### 3.2 Engine `list_tasks` Return Type

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| A) Convert at end of `list_tasks` | Engine owns projection (brief O2); single conversion point | 2 engine tests break (see 3.4) | **0.85** |
| B) Separate `list_task_summaries()` method | No existing test breakage | Violates AC ("list_tasks returns list[TaskSummary]"); two methods to maintain | 0.40 |
| C) Convert in server only | No engine changes | Violates AC; engine doesn't own projection | 0.30 |

**Recommended: Option A.** Filter/sort/limit on full `TaskRecord` internally, then project to `TaskSummary` via `model_validate(t.model_dump())` before return. This preserves filter correctness (needs `claimed_by` for `unclaimed`, `body` for `search`).

### 3.3 Server Simplification

| Current (S2) | After |
|--------------|-------|
| `_strip` set of 12 field names | Eliminated — engine returns `TaskSummary` |
| Manual loop: `{k:v for k,v in raw.items() if k not in _strip}` | `[r.model_dump() for r in records]` |
| Manual `row["claimed"] = record.claimed_by is not None` | Handled by `TaskSummary._coerce_claimed` |
| Hand-built `outputSchema` dict (24 lines) | `TaskSummary.model_json_schema()` in wrapper |

### 3.4 Test Impact Matrix

| Test file | Assertion | Breaks? | Cause | Fix scope |
|-----------|-----------|---------|-------|-----------|
| `test_kanban_engine_listing.py:183` | `isinstance(rec, TaskRecord)` | **YES** | Returns `TaskSummary` now | Update to `isinstance(rec, TaskSummary)` |
| `test_kanban_engine_listing.py:321` | `t.claimed_by is None` | **YES** | `TaskSummary` has `claimed: bool` | Update to `t.claimed is False` |
| `test_kanban_mcp_migration.py` (MCP layer) | Dict key checks | No | Server still returns `list[dict]` | — |
| `test_kanban_engine_roundtrip.py` | Count parity only | No | No field access on results | — |
| `test_kanban_engine_crud.py:445` | `list_tasks()` count after archive | No | Count check only | — |

**O4 compatibility: confirmed.** All MCP-level tests (S6) check dict keys, not object types. The `claimed` bool, stripped fields, and empty-list behaviors are preserved by the `TaskSummary` model approach.

### 3.5 outputSchema Approach

Current manual schema (S2 lines 157-181) wraps in `{"type":"object","properties":{"result":{...}}}`. The `KanbanTask` schema patching (S2 lines 430-438) uses `model_json_schema()` directly. For `list_tasks` (returns array), use:

```python
_list_tasks_tool_obj.fn_metadata.output_schema = {
    "type": "array",
    "items": TaskSummary.model_json_schema(),
}
```

This auto-generates from the model and stays in sync with field changes.

### 3.6 AC File Name Note

AC references `engine_models.py` but the actual file is `models.py` (S1). The model lives at `serve/kanban/src/owlbear_kanban/models.py`. No file rename needed — naming inconsistency from planning phase.

## 4. Recommendation (confidence: 0.88)

Implement Option A: update `TaskSummary` with `extra="ignore"` + `_coerce_claimed` validator, convert at end of engine `list_tasks`, simplify server `_strip` → `model_dump()`, auto-generate `outputSchema`. Two engine test assertions need updating (follow-up task).

Challenge: FALLBACK — trivial GREEN implementation of planned model, no design decision requiring challenger.
Tier: T1 — Autonomous (implementing a planned model change per the approved brief).

## 5. Follow-up Tasks

- **#NEW-1**: Update 2 engine test assertions in `test_kanban_engine_listing.py` broken by `list_tasks` return type change (`TaskRecord` → `TaskSummary`). Needed for GREEN phase.
