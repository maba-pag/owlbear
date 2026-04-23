# Engine Write-Before-Log Atomicity

> **Owning task:** #1104 — Engine write-before-log atomicity: append-failure resilience tests
> **Date:** 2026-04-22 **Status:** Complete

## 1. Context and Question

All 6 engine mutators (`edit_task`, `move_task`, `claim_task`, `end_work`, `sweep`, `release_task`) persist task state via `write_task()` before appending the canonical activity event via `_emit_event()`. If `append_activity_event()` fails after the task write, board state is changed but `activity.jsonl` is missing the corresponding event, breaking `list_sessions()` derivation.

**Design question:** Should the engine (a) rollback task state on append failure, or (b) propagate the exception without rollback? The task AC leaves this as TBD for architect review.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Brief B §3.7 D41 | `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md` L150–162 | 1.0 — atomicity invariant |
| 2 | Brief C §7.1 | `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md` L585–599 | 1.0 — activity.jsonl contract |
| 3 | Engine mutators | `serve/kanban/src/owlbear_kanban/engine.py` L748–1051 | 1.0 — current write-then-log pattern |
| 4 | `write_task()` | `serve/kanban/src/owlbear_kanban/task_io.py` L229–265 | 1.0 — atomic temp+rename |
| 5 | `append_activity_event()` | `serve/kanban/src/owlbear_kanban/activity_store.py` L31–42 | 1.0 — locked append |
| 6 | `_emit_event()` | `serve/kanban/src/owlbear_kanban/engine.py` L1177–1199 | 1.0 — event dispatch |
| 7 | Existing activity tests | `serve/kanban/tests/test_engine_activity.py` | 0.9 — happy-path only |
| 8 | WAL pattern (Wikipedia) | https://en.wikipedia.org/wiki/Write-ahead_logging | 0.5 — general reference |
| 9 | Repo memory note | `/memories/repo/review-activity-log-atomicity.md` | 1.0 — prior reviewer finding |

## 3. Analysis

### Current failure modes (all 6 mutators)

Each mutator follows: `read → mutate → write_task() → _emit_event()`. If `_emit_event()` raises after `write_task()` completes:

- Task file has new state (authoritative board state is changed)
- `activity.jsonl` is missing the event (authoritative operational history is incomplete)
- `list_sessions()` derivation breaks (claim events missing → sessions not opened; end_work events missing → sessions not closed)
- `sweep()` additionally iterates multiple tasks — a mid-loop failure leaves partial sweep state

### Design options comparison

| Criterion | A: Rollback | B: Propagate | C: Log-ahead |
|-----------|------------|-------------|-------------|
| D41 compliance | Full (no partial application) | Partial (task state changed, event missing) | Creates false history — **rejected** |
| Implementation complexity | Medium (~15 LOC per mutator wrapper) | Zero (current behavior + exception bubbling) | Low but **unsafe** |
| Board state correctness | Task file unchanged on failure | Task file has new state | Task file unchanged but event is false |
| Session derivation | Consistent (no event ↔ no task change) | Inconsistent (task changed, event missing) | Inconsistent (event present, task unchanged) |
| Rollback failure risk | Low (write_task uses atomic rename; double-failure = disk error) | N/A | N/A |
| Archive path (`move_task`, `end_work`) | Complex: must undo `_move_file` too | Simple: state is already moved | Does not solve multi-file gap |
| `sweep()` partial iteration | Must rollback per-task within loop | Per-task exception can break loop | Same problem |

### Why log-ahead was rejected

Challenger (confidence: 0.33, block) identified critical flaws:
- False authoritative history: orphan events create phantom sessions (claim logged but task unclaimed) or false closures (end_work logged but task still claimed)
- `ActivityEvent` has no provisional/committed marker; compaction cannot reconcile against task files
- False-positive history is worse than false-negative: the current defect loses events after real mutations; log-ahead asserts mutations that never happened

### D41 scope analysis

D41's explicit examples (predicate failure, forbidden-parameter, OCC failure, cross-reference failure) all concern **pre-mutation validation failures**. None mention post-mutation activity-log failures. Two readings:

- **Broad D41:** "engine write" encompasses both task file + activity event → rollback required
- **Narrow D41:** atomicity applies to task-state mutations; activity log is a separate operational surface → propagate is acceptable

Both readings are defensible. The architect must decide.

## 4. Recommendation

**Option A (Rollback) is the safer default** (confidence: .72), but **Option B (Propagate) is defensible** if the architect scopes D41 narrowly to task-state-only atomicity.

Recommended test design should support BOTH paths:
- **Common:** inject `append_activity_event` failure via `unittest.mock.patch` for all 6 mutators
- **Rollback tests:** assert task file unchanged after failure, exception propagates
- **Propagate tests:** assert exception propagates with activity-write root cause, task state IS changed

The test file should use a parametric design where the assertion mode (rollback vs propagate) is configurable, so the architect can flip the switch at review time.

Challenge: **block → revised** — log-ahead rejected, recommendation narrowed to rollback vs propagate. Confidence in revised: .72.

## 5. Follow-up Tasks

1. **Test task:** Write failure-injection tests for all 6 mutators (test-writer scope)
2. **Implementation task:** Engine mutator atomicity wrapper (builder scope, depends on architect decision)
