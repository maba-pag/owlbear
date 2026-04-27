# Add expected_updated CAS param to engine.release_task

> **Owning task:** #1133 — Add expected_updated CAS param to engine.release_task
> **Date:** 2026-04-27 **Status:** Complete

## 1. Context and Question

`engine.release_task()` is the only mutating engine method without OCC support. Both `edit_task` and `move_task` accept an optional `expected_updated` parameter and use `write_task_if_unchanged` for compare-and-swap writes. `CockpitView` wraps edit/move with required OCC, but `CockpitView.release_task` remains last-writer-wins.

**Question:** How should the existing `expected_updated` pattern be extended to `release_task`, given that release has a no-op early-return path that edit/move lack?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `engine.py` L1266–1320 — `release_task` (current LWW) | 1.0 |
| 2 | `engine.py` L1050–1065 — `edit_task` CAS branch | 1.0 |
| 3 | `engine.py` L1130–1145 — `move_task` CAS branch | 1.0 |
| 4 | `engine.py` L3204–3217 — `CockpitView.release_task` | 1.0 |
| 5 | `engine.py` L3119–3177 — `CockpitView.edit_task` (required OCC) | 0.9 |
| 6 | `engine.py` L3179–3203 — `CockpitView.move_task` (required OCC) | 0.9 |
| 7 | `storage.py` L412–453 — `write_task_if_unchanged` | 0.9 |
| 8 | `errors.py` L70–72 — `ConcurrencyError` | 0.8 |
| 9 | `.owlbear/research/cockpit-mutation-occ-parity.md` (#1130 parent) | 0.8 |

## 3. Analysis

### Existing Pattern (edit_task / move_task)

```
read_task → mutate fields → set updated = now
  if expected_updated: write_task_if_unchanged(record, expected_updated, dir)
  else:                write_task(record, dir)
emit_event → on failure: rollback via write_task(original, dir)
```

### Design Consideration: No-Op Path

`release_task` has an early return when `claimed_at is None` — edit/move always write. With CAS:

| Scenario | claimed_at | expected_updated | Correct behavior |
|----------|-----------|-----------------|------------------|
| Normal release | set | provided | CAS write via `write_task_if_unchanged` |
| Agent release (LWW) | set | None | `write_task` (unchanged behavior) |
| Already released, stale token | None | provided, stale | **ConcurrencyError** — snapshot was stale |
| Already released, fresh token | None | provided, fresh | No-op return (desired state achieved) |
| Already released, no token | None | None | No-op return (unchanged behavior) |

**Key insight:** When `expected_updated` is provided, the token must be verified *before* the no-op early return. A stale UI showing a task as claimed (snapshot at T1) shouldn't silently succeed when the task was released (T2) and reclaimed by another agent (T3). The pre-check catches `T1 != T3`.

**Implementation approach:**

```
read_task(task_path)
if expected_updated is not None and record.updated != expected_updated:
    raise ConcurrencyError(ERR_STALE)
if record.claimed_at is None:
    return record  # no-op
# ... proceed with release, use write_task_if_unchanged when expected_updated set
```

The pre-check is racy (no lock), but the write path has the authoritative locked check via `write_task_if_unchanged`. The no-op path only needs the optimistic check since no write occurs.

### CockpitView Changes

Current `CockpitView.release_task` does a separate `show_task` then conditionally calls `engine.release_task`. With engine-level CAS, simplify to pass `expected_updated` through — the engine handles no-op + CAS atomically.

### Rollback Path

Rollback on event emission failure continues to use `write_task(original, ...)` unconditionally, same as edit/move. This is correct — restoring the original should be force-written.

## 4. Recommendation

**Direct pattern replication + no-op CAS pre-check** — confidence: 0.90

The implementation is mechanical: add `expected_updated: str | None = None` to `engine.release_task`, branch on it for the write, add a pre-check before the no-op return. CockpitView gets required `expected_updated: str` parameter and passes it through.

Challenge: SKIP — trivial pattern extension, no novel decisions.

## 5. Follow-up Tasks

No additional follow-ups needed. Task #1133 IS the follow-up from #1130 research. Route wiring is already tracked as #1132.
