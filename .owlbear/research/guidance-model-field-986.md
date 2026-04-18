# Guidance Model Field — KanbanTask

> **Owning task:** #986 — Add `guidance: list[str]` field to KanbanTask model
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Decision D4 (locked) specifies: `guidance: list[str] = []` as **first declared field** on `KanbanTask`, with Pydantic v2 declaration-order placing it first in JSON output. This research verifies the technical claims and confirms no downstream breakage.

## 2. Sources Studied

| Source | Type | Relevance | What |
|--------|------|-----------|------|
| Pydantic 2.12.5 runtime verification | Empirical | 1.0 | Confirmed declaration-order serialization, `model_validate` default-fill |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Codebase | 1.0 | Current KanbanTask model — `extra="ignore"`, existing `Field(default_factory=list)` pattern for `tags`/`depends_on` |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Codebase | 1.0 | `_record_to_task`: `KanbanTask.model_validate(record.model_dump())` — auto-fills missing fields |
| `serve/kanban/src/owlbear_kanban/models.py` | Codebase | 0.9 | Engine `Task` model — no `guidance` field, uses `extra="allow"` |
| Cockpit routes (`read.py`, `mutation.py`) | Codebase | 0.8 | Re-serializes field-by-field into `TaskDetailOut`/`TaskSummaryOut` — not affected by KanbanTask changes |
| `.owlbear/research/block-time-guidance-mcp-973.md` | Research | 0.9 | Parent feature research — confirms no engine-layer changes needed |

## 3. Analysis

### Verified Claims

| Claim | Result | Evidence |
|-------|--------|----------|
| Declaration-order serialization | **PASS** | `model_dump()` returns keys in declaration order (Pydantic 2.12.5) |
| `model_validate` fills `guidance=[]` when key missing | **PASS** | Empirical test: `KanbanLike.model_validate(data)` → `guidance=[]` |
| `_record_to_task` needs no change | **PASS** | Engine `Task.model_dump()` omits `guidance`; Pydantic auto-defaults |
| `extra="ignore"` doesn't interfere | **PASS** | `extra="ignore"` ignores unknown keys, doesn't reject missing keys |
| No positional field access in consumers | **PASS** | All access is by name; Cockpit re-serializes independently |

### Impact Assessment

| Consumer | Impact | Notes |
|----------|--------|-------|
| MCP tools (`show_task`, `list_tasks`, etc.) | Additive — new key in JSON | `guidance: []` appears in all responses |
| Cockpit backend | **None** | Uses own response models, field-by-field construction |
| Cockpit frontend | **None** | Doesn't consume KanbanTask directly |
| `_record_to_task` | **None** | Pydantic default-fills the missing key |
| Existing tests | **None** | No assertions on JSON key order or field count |

### Risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| Agent confusion from new empty field | Low | Field is always `[]` until guidance module (#987) populates it |
| JSON payload size increase | Negligible | `"guidance": []` adds ~15 bytes per task |

## 4. Recommendation

Proceed with implementation as specified in D4 and AC. Confidence: **.95**

Challenge: SKIPPED — trivial model field addition, decision D4 locked, no alternatives to evaluate.

## 5. Follow-up Tasks

No new follow-up tasks needed — downstream work (#987 guidance module, #985/#989/#991 tool wiring) already exists as subtasks of #973.

### Implementation Notes for Downstream

- Use `Field(default_factory=list)` (not bare `= []`) — consistent with existing `tags`/`depends_on` pattern.
- Test file: `serve/mcp-kanban/tests/test_guidance_model_973.py` (grouped under parent feature).
- Three AC-specified unit tests cover: field existence/default, JSON key order, engine-dict roundtrip.
