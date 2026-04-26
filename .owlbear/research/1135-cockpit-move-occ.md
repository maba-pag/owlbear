# Add OCC Token to Cockpit Move Route

> **Owning task:** #1135 — Add OCC token to cockpit move route
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

The cockpit move route (`POST /tasks/{id}/move`) has no optimistic concurrency control. `MoveRequest` carries only `status`; the route calls `engine.move_task()` without `expected_updated`. Two concurrent moves can race without detection. The engine supports `expected_updated` (CAS via `write_task_if_unchanged`) and `CockpitView.move_task()` already requires it — but the HTTP route bypasses `CockpitView`.

**Question:** What approach should the implementation use, and what are the test implications?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` L28-33, L84-100 | 1.0 | `MoveRequest` model, move route handler |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` L1068-1160 | 1.0 | `move_task()` with `expected_updated` CAS path |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` L3174-3199 | 0.9 | `CockpitView.move_task()` — reference pattern |
| S4 | `serve/kanban/src/owlbear_kanban/errors.py` L70 | 0.8 | `ConcurrencyError` definition |
| S5 | `tests/test_cockpit_mutation_api.py` L137-175 | 0.9 | Existing move tests (need `updated` field) |
| S6 | `tests/test_cockpit_mutation_api.py` L286-300 | 0.8 | Stale edit test — pattern for stale move test |
| S7 | `.owlbear/research/1131-cockpit-mutation-race-tests.md` §G2 | 0.9 | Gap analysis establishing the need |

## 3. Analysis

### 3.1 Approach Comparison

| Criterion | A: Precheck only | B: Engine CAS only | C: Precheck + CAS |
|-----------|-------------------|--------------------|--------------------|
| TOCTOU gap | Yes — race between `show_task` and `move_task` | No — atomic CAS at write time | No — CAS covers the gap |
| Fast-fail for stale tokens | Yes — immediate 409 before engine call | No — engine does the check | Yes — precheck fast-fails obvious cases |
| Consistency with edit route | Matches current edit pattern | Matches #1134's target pattern | Matches #1134's planned belt-and-suspenders |
| Consistency with CockpitView | No — CockpitView uses engine CAS | Yes — same mechanism | Yes |
| `ConcurrencyError` handler needed | No | Yes | Yes |
| Lines of change | ~5 | ~10 | ~12 |

### 3.2 Key Facts

- `engine.move_task()` already has `expected_updated: str | None = None` — CAS is off by default, engaged when non-None
- `ConcurrencyError` lives in `owlbear_kanban.errors` — not in `__init__.py` public API, import from `owlbear_kanban.errors` directly
- The move route already calls `engine.show_task()` to get the task (for transition validation) — the `task.updated` value is already available at no extra cost
- `MoveRequest` uses `extra="forbid"` — adding a required `updated` field is a breaking contract change for existing clients (intentional per AC)
- Existing 5 move tests all send `{"status": "..."}` without `updated` — all need update
- The edit route detail string is `"Task was modified since your last load (stale snapshot)"` — reuse for consistency

### 3.3 Implementation Approach (Recommended: C)

1. Add `updated: str` to `MoveRequest` (required field)
2. Keep the `show_task` call (needed for transition validation anyway)
3. Add precheck: `req.updated != str(task.updated)` → 409 (fast-fail, consistent with edit)
4. Pass `expected_updated=req.updated` to `engine.move_task()` (true CAS)
5. Import `ConcurrencyError` from `owlbear_kanban.errors`
6. Catch `ConcurrencyError` → 409 with same detail string as edit route

### 3.4 Test Changes

| Test | Change needed |
|------|---------------|
| All 5 existing move tests | Add `updated` field from `engine.show_task("1").updated` to request body |
| `test_move_happy_path_returns_200` | Add `updated` to json payload |
| `test_move_returns_updated_task_object` | Add `updated` to json payload |
| `test_move_invalid_target_status_returns_422` | Add `updated` to json payload |
| `test_move_same_status_returns_422` | Already gets task from engine — add `updated` |
| `test_move_nonexistent_task_returns_404` | No `updated` needed — 404 before OCC check |
| **New:** `test_move_stale_updated_returns_409` | Mutate task between load and move; assert 409 |
| Activity log tests for move | Add `updated` to json payload |
| Audit log tests for move | Add `updated` to json payload |

### 3.5 Relationship to #1134

Both #1134 (edit) and #1135 (move) add `ConcurrencyError` handling. They can be implemented in either order. The `ConcurrencyError` import and 409 handler pattern will be shared. No blocking dependency.

## 4. Recommendation (confidence: 0.92)

Use **Approach C** (precheck + engine CAS). Rationale:
- Precheck is nearly free (task already loaded for transition validation)
- Engine CAS eliminates the TOCTOU gap
- Consistent with #1134's direction for the edit route
- Reuses the same 409 detail string for client predictability

Risk: Low. All engine plumbing exists; this is pure route-layer wiring.

Challenge: skipped — near-trivial wiring of existing engine CAS; zero ambiguity on mechanism.

## 5. Follow-up Tasks

No additional follow-up tasks needed. #1135 itself is the implementation task — this research validates the approach and advances it to backlog.
