# Fix Edit Route CAS Gap

> **Owning task:** #1134 — Fix edit route to pass expected_updated to engine and handle ConcurrencyError
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

The cockpit edit route (`mutation.py`) has a TOCTOU gap: it does a string-comparison precheck (`req.updated != task.updated` → 409) but never passes `expected_updated` to `engine.edit_task()`. The engine's compare-and-swap mechanism is never engaged. If it were, `ConcurrencyError` would propagate as an unhandled 500.

**Question:** What's the minimal fix, and what are the trade-offs of keeping vs removing the route-level precheck?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` L186-211 | 1.0 | Edit route: precheck present, `expected_updated` not passed, no `ConcurrencyError` handler |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` L939-960 | 1.0 | `edit_task` signature: `expected_updated: str \| None = None` |
| S3 | `serve/kanban/src/owlbear_kanban/engine.py` L1050-1056 | 1.0 | Engine CAS: `write_task_if_unchanged(record, expected_updated, ...)` |
| S4 | `serve/kanban/src/owlbear_kanban/engine.py` L3114-3170 | 0.9 | `CockpitView.edit_task` — reference pattern: passes `expected_updated`, catches `ConcurrencyError` |
| S5 | `serve/kanban/src/owlbear_kanban/errors.py` L70-71 | 0.9 | `ConcurrencyError(KanbanError)` definition |
| S6 | `serve/kanban/src/owlbear_kanban/storage.py` L430-452 | 0.8 | `write_task_if_unchanged` raises `ConcurrencyError(code="ERR_STALE")` |
| S7 | `.owlbear/research/1131-cockpit-mutation-race-tests.md` §3.2 G1 | 0.8 | Prior analysis identifying this gap |

## 3. Analysis

### 3.1 Current vs Required Behavior

| Aspect | Current | Required |
|--------|---------|----------|
| Route precheck | `req.updated != str(task.updated)` → 409 | Optional fast-fail (TOCTOU window exists) |
| Engine CAS | Not engaged (`expected_updated` not passed) | Engaged via `expected_updated=req.updated` |
| `ConcurrencyError` handling | Not imported, would be 500 | Caught → 409 with stable detail string |
| Import of `ConcurrencyError` | Missing | `from owlbear_kanban.models import ConcurrencyError` |

### 3.2 Fix Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Add CAS + keep precheck | Pass `expected_updated` to engine, add `ConcurrencyError` → 409 handler, keep route precheck as fast-fail | Fast-fail avoids engine round-trip on obvious stale; defense-in-depth | Two OCC checks (redundant but harmless) |
| B: Add CAS + remove precheck | Pass `expected_updated` to engine, add handler, remove route precheck entirely | Single OCC layer; simpler code | Slightly slower stale rejection (engine does full read+compare+write) |

### 3.3 Implementation Specifics

The fix is ~8 LOC in `mutation.py`:

1. **Import:** `from owlbear_kanban.models import ConcurrencyError` (runtime, not TYPE_CHECKING — needed for `except`)
2. **Pass CAS token:** Add `expected_updated=req.updated` to `engine.edit_task(str(task_id), **kwargs)` — either inject into `kwargs` or pass as separate kwarg
3. **Handler:** Wrap `engine.edit_task` call with `except ConcurrencyError` → `HTTPException(409, detail="Task was modified since your last load (stale snapshot)")` — reuse same detail string as precheck for API stability

The route precheck (L195-199) can stay as a fast-fail optimization — it catches obviously stale requests before building kwargs and calling the engine.

### 3.4 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Detail string divergence between precheck and CAS handler | Low | Use same literal string in both paths |
| `ConcurrencyError` import creates runtime coupling | Low | Already depends on `owlbear_kanban.KanbanEngine` at runtime via DI |
| Engine CAS changes behavior subtly | Minimal | Engine CAS is well-tested (S3, S6); only adds a stronger guarantee |

## 4. Recommendation (confidence: 0.90)

**Option A: Add CAS + keep precheck.** The precheck is a cheap fast-fail that avoids `_build_edit_kwargs` work on obviously stale requests. The engine CAS closes the TOCTOU window. Both return the same 409 detail string for API stability.

This is a T1 (autonomous bug fix) — no architecture change, no new capability, no user-facing behavior change beyond closing a correctness gap.

Challenge: skipped — trivial single-option fix with clear prior analysis in #1131. Confidence 0.90.

## 5. Follow-up Tasks

No additional follow-ups needed — #1134 itself is the implementation task. AC is well-specified.
