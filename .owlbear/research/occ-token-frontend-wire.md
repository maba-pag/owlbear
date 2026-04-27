# Wire OCC Token Through Cockpit Frontend Move Flow

> **Owning task:** #1137 — Wire updated OCC token through cockpit frontend move flow
> **Date:** 2026-04-27 **Status:** Complete

## 1. Context and Question

Task #1135 made `MoveRequest.updated` required on the backend mutation route. The `POST /tasks/{id}/move` endpoint now returns 409 if `updated` doesn't match the task's current timestamp (OCC check). The frontend currently sends only `{ status }` and the read API's `TaskSummaryOut` lacks `updated`, so every move request will 422 until the wire-up is complete.

**Question:** What is the minimal, KISS-aligned approach to flow `updated` from the kanban engine through the cockpit API to the frontend move request?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/models.py` — `TaskSummary`, `TaskFull`, `Task` | Codebase | 1.0 |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` — `list_tasks` (lines 795–814) | Codebase | 1.0 |
| 3 | `serve/cockpit/src/owlbear_cockpit/models.py` — `TaskSummaryOut` | Codebase | 1.0 |
| 4 | `serve/cockpit/src/owlbear_cockpit/routes/read.py` — `list_tasks` route | Codebase | 1.0 |
| 5 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — `MoveRequest`, `move_task` | Codebase | 1.0 |
| 6 | `serve/cockpit/web/src/hooks/useBoard.ts` — `Task` interface | Codebase | 1.0 |
| 7 | `serve/cockpit/web/src/KanbanBoard.tsx` — `handleTransitionClick` | Codebase | 1.0 |
| 8 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` — move test fixtures | Codebase | 0.9 |

## 3. Analysis

### Data Flow Gap

```
Engine list_tasks() → Task.model_dump() → TaskSummary.model_validate() [drops updated]
  → Cockpit adapter.list_tasks() → read route → TaskSummaryOut [no updated field]
    → GET /api/tasks → Frontend Task interface [no updated field]
      → handleTransitionClick → POST /move { status } [missing updated → 422]
```

The engine's `list_tasks()` already works with full `Task` objects that include `updated`. It calls `task.model_dump()` then `TaskSummary.model_validate()`. Since `TaskSummary` uses `extra="ignore"`, the `updated` value is silently dropped. The data exists — it's just discarded at the projection step.

### Options Comparison

| Criterion | A: Add `updated` to `TaskSummary` | B: Cockpit adapter enrichment | C: Separate full-task cockpit endpoint |
|-----------|:---:|:---:|:---:|
| Lines changed (kanban) | ~3 (model + docstring) | 0 | 0 |
| Lines changed (cockpit) | ~4 | ~15+ (per-task show_task calls) | ~20+ (new route + adapter) |
| Lines changed (frontend) | ~6 | ~6 | ~6 |
| Caching impact | None — data already computed | Defeats MtimeScanCache (N+1 queries) | New cache path needed |
| KISS alignment | High | Low | Low |
| Risk | `TaskFull.updated` becomes redundant redeclaration (harmless in Pydantic) | Performance regression on large boards | Over-engineering |
| MCP consumer impact | `list_tasks` responses gain `updated` (benign — more data) | None | None |

### Key Observations

1. **`TaskFull(TaskSummary)` inheritance:** `TaskFull` adds `created`, `updated`, `body` on top of `TaskSummary`. Adding `updated` to `TaskSummary` makes the `TaskFull.updated` a harmless override. No functional change — Pydantic handles parent/child field redeclaration cleanly.
2. **Frontend OCC refresh:** `handleTransitionClick` ignores the `TaskDetailOut` response and calls `refetchTasks()`. The next `GET /api/tasks` poll provides the new `updated` value, so the OCC token stays fresh without additional wiring.
3. **Edit and release routes:** `EditRequest` also requires `updated`. The same wire-up pattern applies to any future edit UI. Surfacing `updated` in the task list benefits those flows too.
4. **Test fixtures:** All mock task objects in `KanbanBoard.test.tsx` (`TASKS`, `TASKS_AFTER_MOVE`) need `updated` fields. The move assertion must include `updated` in the expected `body`.

## 4. Recommendation

**Option A: Add `updated` to `TaskSummary`** — confidence: **0.90**

This is the simplest approach. The data already exists and is discarded at projection. One field addition to `TaskSummary` flows through adapter → read API → frontend with minimal wiring. No new endpoints, no caching changes, no N+1 queries.

Challenge: FALLBACK — trivial wire-up research, no architectural trade-off warrants formal challenge.

### Implementation Plan (6 files, ~25 LOC net)

| Layer | File | Change |
|-------|------|--------|
| Kanban model | `serve/kanban/src/owlbear_kanban/models.py` | Add `updated: str` to `TaskSummary`; update docstring |
| Kanban model test | `serve/kanban/tests/test_engine_models.py` | Verify `updated` present on `TaskSummary` |
| Cockpit model | `serve/cockpit/src/owlbear_cockpit/models.py` | Add `updated: str` to `TaskSummaryOut` |
| Cockpit read route | `serve/cockpit/src/owlbear_cockpit/routes/read.py` | Include `updated=s.updated` in `TaskSummaryOut` construction |
| Frontend hook | `serve/cockpit/web/src/hooks/useBoard.ts` | Add `updated: string` to `Task` interface |
| Frontend component | `serve/cockpit/web/src/KanbanBoard.tsx` | Include `updated` in `handleTransitionClick` `JSON.stringify` |
| Frontend test | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` | Add `updated` to all fixture tasks; update move assertion |

## 5. Follow-up Tasks

- Task to implement the wire-up (backlog-ready after research)
- No decision requests needed — T1 change (bug fix: frontend broken by #1135 contract change)
