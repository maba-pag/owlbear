# Fix release outcome to append notes per Brief B D52

> **Owning task:** #1127 — Fix release outcome to append notes per Brief B D52
> **Date:** 2026-04-25 **Status:** Complete

## 1. Context and Question

Brief B D52 specifies: "`release`: clears claim, no status change, `note` appended if set."
The current `AgentView.end_work(outcome="release")` routes to `engine.release_task()`, which clears the claim but does **not** append any note. This is defect D2 from the parent #1124 reconciliation research.

**Question:** What is the safest, KISS-aligned implementation approach to add note-appending to the release outcome?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | Brief B D52 (`decisions.md` L214) | Authority | 1.0 |
| 2 | Brief B D55 (`decisions.md` L232) | Authority | 1.0 |
| 3 | `engine.py` AgentView.end_work (L2757–2991) | Code | 1.0 |
| 4 | `engine.py` KanbanEngine.end_work (L1348–1460) | Code | 1.0 |
| 5 | `engine.py` KanbanEngine.release_task (L1252–1293) | Code | 1.0 |
| 6 | `engine.py` _collect_task_sessions (L242–310) | Code | 0.9 |
| 7 | `engine.py` _classify_end_work_state/outcome (L190–215) | Code | 0.9 |
| 8 | `engine.py` _SESSION_FILTER_STATES (L333–340) | Code | 0.8 |
| 9 | `activity_store.py` _close_actions (L268, 282) | Code | 0.8 |
| 10 | `cockpit/web/src/components/ActivityTab.tsx` (L16–30) | Code | 0.7 |
| 11 | Parent research: `.owlbear/research/reconcile-end-work-outcome-contract-v2.md` | Prior art | 0.9 |
| 12 | `test_engine_end_work_1077.py` (L279–340) | Test | 0.8 |

## 3. Analysis

### 3.1 Current release flow (AgentView)

1. AgentView validates parameter matrix (move_to/archival/block forbidden for release)
2. If unclaimed → pure no-op, returns unchanged task (D55)
3. If claimed → calls `engine.release_task(task_id, source="agent")`
4. `release_task` clears claim fields, writes, emits event `action="release"` / `detail="released by agent"`
5. **Note is silently discarded** — never reaches the body

### 3.2 Session analytics impact of event-type change

The session classifier dispatches on `action`:

| Current path | Event action | Session state | Session outcome |
|-------------|--------------|---------------|-----------------|
| `release_task` | `"release"` | `"released"` | `"release"` |
| `engine.end_work` (hypothetical) | `"end_work"` | `"released"` | `"released"` |

Routing release through `engine.end_work` changes session outcome from `"release"` to `"released"` (via `_classify_end_work_outcome`). Also creates inconsistency: CockpitView.release_task still emits `action="release"`, so the same logical operation emits different event types depending on the caller.

### 3.3 Note-format contract

The timestamped note format (`stamp + "\n" + note`) is defined in `engine.end_work` L1410–1411:
```
stamp = now.replace(microsecond=0).isoformat()
record.body = body + "\n" + stamp + "\n" + note
```
Any duplication risks format drift if this format is later changed.

### 3.4 Option trade-off matrix

| Criterion | A: Route through end_work | B: Add note to release_task | C: Extract helper + add to release_task |
|-----------|---------------------------|-----------------------------|-----------------------------------------|
| **AC4 compliance** | Ambiguous (action type changes) | Clean | Clean |
| **Session data contract** | outcome changes "release"→"released" | Unchanged | Unchanged |
| **DRY** | Single path | 2 locations (format drift risk) | Single helper (no drift) |
| **Change surface (engine)** | ~15 lines (valid_outcomes, guard, _apply_outcome, routing) | ~8 lines (release_task sig + body) | ~12 lines (helper + release_task + end_work refactor) |
| **Event consistency** | Diverges (agent=end_work, cockpit=release) | Preserved | Preserved |
| **Atomicity** | Inherited from end_work | release_task already atomic | release_task already atomic |
| **Unclaimed-task guard** | Inherited from view layer | Widens engine-level gap (view guards) | Same as B (view guards) |
| **KISS score** | 0.50 | 0.70 | 0.80 |
| **Confidence** | 0.50 | 0.65 | 0.75 |

### 3.5 Key finding: dead guard in engine.end_work

`engine.end_work` L1409 has `if outcome != "release":` but `"release"` is not in its `valid_outcomes`. This is defensive dead code — evidence the routing was considered but not wired up. Option A would activate it by adding `"release"` to `valid_outcomes` and removing the guard.

## 4. Recommendation

**Option C — Extract `_append_timestamped_note` helper, call from both `end_work` and `release_task`** (confidence: 0.75)

This combines Option B's event-path stability with Option A's DRY guarantee. The helper is ~3 lines and has exactly 2 callers — YAGNI doesn't apply. AC4 is satisfied by default since `release_task` retains its event type. No session analytics impact.

Implementation sketch:
1. Extract `_append_timestamped_note(record, note, now)` as a private method on `KanbanEngine`
2. Call from `end_work` (replacing inline note logic) and from `release_task` (when note is provided)
3. Add `note: str | None = None` parameter to `release_task()`
4. AgentView passes `note` to `release_task()` when claimed
5. Update existing release tests to assert note IS appended when provided

**Tier: T1 (autonomous).** This is a D52 implementation bug fix — no new capability, no architecture change, no security impact. The parent research (#1124) already classified it as T1/D2.

### Challenge results

Challenge: `reconsider` — confidence in original (Option B): 0.55
Key challenges: (1) DRY risk underpriced — format drift between two note-appending sites, (2) Option C (helper extraction) captures best of both approaches, (3) engine-level unclaimed-task guard gap in Option B, (4) dead `if outcome != "release":` guard is evidence of original Option A intent
Researcher response: revised from B to C — accepted the DRY concern and helper proposal. The 3-line helper is justified with 2 callers and prevents format drift.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #1127 itself moves from research → backlog for implementation. The implementation approach (Option C) is fully specified above.
