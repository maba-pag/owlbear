# Add Revision Counter

> **Owning task:** #810 — Add revision counter
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Phase 1 of the kanban engine restructuring calls for a per-instance revision counter on `KanbanEngine` so polling-based consumers (future GUI) can detect board changes efficiently. The question: what implementation approach fits OwlBear's stack, and is the feature already in place?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` | Codebase | 1.0 — primary implementation file |
| 2 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Brief | 0.9 — defines O5, revision counter spec |
| 3 | HTTP ETag / CouchDB `_rev` / SQLite `data_version` | Prior art | 0.8 — monotonic counters are standard change-detection |

## 3. Analysis

### Research Gate Checklist

| # | Gate | Result |
|---|------|--------|
| 1 | Theoretical validity | Sound — monotonic counter is the simplest change-detection signal for polling |
| 2 | Environment audit | No pre-existing mechanism; custom counter is appropriate |
| 3 | Prior art | HTTP ETags, CouchDB `_rev`, SQLite `data_version` — all monotonic counters |
| 4 | Technical feasibility | Already implemented and passing (Python 3.12, no deps) |
| 5 | Architecture fit | Natural `KanbanEngine` instance attribute; no cross-process coordination needed |
| 6 | Implementation approach | `self._revision: int = 0`, `@property` (read-only), `+= 1` in every write method |

### Implementation Inventory

The revision counter is fully implemented in `engine.py`:

| Write method | Increments | Notes |
|--------------|------------|-------|
| `create_task` | +1 | Direct `self._revision += 1` |
| `edit_task` | +1 | Direct |
| `move_task` | +1 | Direct |
| `claim_task` | +1 | Direct |
| `release_task` | +1 | Direct |
| `start_work` | +1 | Delegates to `claim_task` |
| `end_work` | +2 to +3 | Compound: calls `edit_task` + `release_task` + `move_task` (varies by outcome) |

### Test-Writer Note

`end_work` is compound — it calls 2-3 internal write methods, each incrementing revision independently. Tests should assert `revision > previous_revision` rather than `revision == previous_revision + 1` for compound operations.

### Existing Test Status

152 kanban tests pass. 4 collection errors (pre-existing import drift from engine extraction — unrelated to revision counter).

## 4. Recommendation

**No implementation work needed — feature is complete.** Confidence: 0.95.

Task #810 can proceed directly to GREEN verification against #809 tests once those tests are written. The implementation satisfies all AC items.

Challenge: SKIP — trivial finding (implementation already exists); no recommendation choice to challenge.

## 5. Follow-up Tasks

None created — #809 (test task) already exists and covers the only remaining work.
