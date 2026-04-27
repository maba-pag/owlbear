# Cockpit Durable Suite ↔ Brief B Reconciliation

> **Owning task:** #1144 — Reconcile durable cockpit suites with Brief-B contract migration
> **Date:** 2026-04-27  **Status:** Complete

## 1. Context and Question

Builder #1082 rewrote cockpit routes to delegate to `CockpitView` and return Brief-B canonical models (`ListTasksResponse`, `ShowTaskResponse`, `SingleTaskResponse`). This broke 18 tests in the durable suites (`test_cockpit_read_api.py`, `test_cockpit_mutation_api.py`) that assert the pre-Brief-B cockpit contract.

**Question:** What are the exact gaps, how should each be resolved, and does the 1082 test suite conflict with the durable suite?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/cockpit/src/owlbear_cockpit/routes/read.py` | Live code | Current route implementations |
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | Live code | Edit route missing block:user logic |
| `serve/kanban/src/owlbear_kanban/models.py` | Live code | `ListTasksResponse` (no mtime), `TaskSummary._coerce_claimed` (drops claimed_by) |
| `serve/kanban/src/owlbear_kanban/engine.py` L3124–3300 | Live code | `CockpitView` facade, `_BLOCK_REASON_UNSET` sentinel |
| `tests/test_cockpit_read_api.py` | Durable tests | 12 failures: 4 mtime, 3 sessions, 5 claimed_by |
| `tests/test_cockpit_mutation_api.py` | Durable tests | 6 failures: all block:user lifecycle |
| `tests/test_cockpit_kanban_routes_1082.py` | 1082 tests | Conflicting assertion: `mtime not in body` |
| `tests/test_cockpit_read_api_930.py` | 930 tests | 3 additional failures (2 mtime, 1 cache-hit) — adjacent scope |
| `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md` | Brief B | ListTasksResponse envelope: `{tasks, missing_ids, guidance}` — no mtime |
| `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/decisions.md` | Brief B | D11 (no claimed_by), D21 (cockpit mutation rewire), D31 (sessions) |

## 3. Analysis

### Gap Inventory (18 failures: 12 read + 6 mutation)

| Gap | Tests | Root Cause | Fix Direction |
|-----|-------|------------|---------------|
| **G1: mtime absent from GET /api/tasks** | 4 read | Route returns `ListTasksResponse` (engine model, no mtime field). `MtimeScanCache` injected but unused. | Inject mtime from cache; use cockpit response model. |
| **G2: Sessions wrapped envelope** | 3 read | Route correctly returns flat `list[SessionRecord]` per Brief B D31. Tests assert legacy `{"sessions": [...]}`. | Update 3 tests to assert flat list. |
| **G3: claimed_by in detail** | 5 read | `ShowTaskResponse` → `TaskSummary._coerce_claimed` drops `claimed_by` per D11. Tests assert field presence. | Update 5 tests: invert to assert absence; rework model tests for `claimed_at`. |
| **G4: block:user lifecycle** | 6 mutation | `_build_edit_kwargs` doesn't inject `block:user` tag on block/unblock. No `_apply_block_kwargs` helper. | Add block:user logic in edit route with conflict resolution. |

### G1 Deep Dive: Mtime Authority Conflict

**Conflict:** The 1082 test `test_list_tasks_envelope_has_no_mtime_field` (passes) asserts mtime is absent. The durable test `test_tasks_response_has_mtime_integer` (fails) asserts mtime is present. Both currently reflect actual behavior.

**Brief B position:** `ListTasksResponse` = `{tasks, missing_ids, guidance}` — no mtime. The 1082 test aligns with this.

**Cockpit frontend need:** The frontend uses mtime for cache invalidation — detecting when to re-fetch. This was part of the original cockpit spec (R2 in #928). Without mtime, the frontend has no change-detection signal.

**Resolution (confidence: 0.82):** The engine `ListTasksResponse` correctly omits mtime — that's not the engine's concern. The cockpit HTTP endpoint should augment the response with mtime as an adapter responsibility. The route needs a cockpit-specific response model that extends the engine envelope with `mtime: int`. The 1082 test conflates the engine envelope shape with the HTTP response shape. **Update 1082 test alongside the route fix.**

Evidence: 6 tests across 2 suites (928, 930) expect mtime. 1 test (1082) expects no mtime. The 1144 AC explicitly mandates injection.

### G4 Deep Dive: Route-State Dependency

The edit route only fetches the current task when `tags` or `depends_on` are in the request fields:

```python
if "tags" in fields or "depends_on" in fields:
    task = view.show_task(task_id)
```

But `_apply_block_kwargs` needs current tag state to check for existing `block:user` (idempotency, AC#975 AC3). When only `block_reason` is sent, the task is not fetched. **The fetch condition must expand to include `block_reason`.**

### Adjacent Scope: 930 Suite (3 failures, not in 1144 AC)

| Failure | Cause | Relationship |
|---------|-------|-------------|
| `test_empty_board_tasks_mtime_is_zero` | No mtime in response | Fixed by G1 |
| `test_mtime_increases_after_new_task_created` | No mtime in response | Fixed by G1 |
| `test_engine_list_tasks_not_called_on_cache_hit` | Cache short-circuit dropped | Separate concern |

G1 fix will also fix 2 of 3 tests in 930. The cache-hit test is a caching optimization that was part of the old cockpit design — separate follow-up.

### Dead Cockpit Models

`TaskSummaryOut`, `TaskDetailOut`, `TaskListOut`, `SessionListOut`, `SessionOut` in `owlbear_cockpit/models.py` are now unused. Routes return engine models directly. Low-priority cleanup.

## 4. Recommendation

**Confidence: 0.80** (revised from 0.85 after challenger).

All 4 gaps are T1 — bug fix/refactor. No new capability, no architecture change, no T3 triggers.

Challenge: `proceed (revised)` — challenger forced re-evaluation of G1 (mtime authority) and G4 (route-state dependency). Original mtime analysis was imprecise about the conflict level. G4 pre-condition gap was not initially identified. Both are now documented.

**Implementation approach (recommended):**

1. **G1 (mtime):** Create a cockpit `CockpitTaskListResponse` model extending engine envelope + `mtime: int`. Route scans cache, augments response. Update 1082 test.
2. **G2 (sessions):** Update 3 test assertions from `body["sessions"]` to `body` (flat list).
3. **G3 (claimed_by):** Update 5 tests: invert claimed_by assertions to assert absence; rework `TaskDetailOut` model test to use `claimed_at`/`ShowTaskResponse`.
4. **G4 (block:user):** Add `_apply_block_kwargs` helper. Expand task-fetch condition to include `block_reason`. Handle conflict resolution with `_apply_list_diff`.

## 5. Follow-up Tasks

| Task | Status | Priority |
|------|--------|----------|
| #1144 itself (advance to backlog) | Implementation-ready | important |
| Cache-hit optimization (930 test) | New task at research | nice-to-have |
| Dead cockpit model cleanup | New task at research | someday |
