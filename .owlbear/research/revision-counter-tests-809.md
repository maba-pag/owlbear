# Revision Counter Tests — Research

> **Owning task:** #809 — Tests — revision counter
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #809 specifies RED tests for a `KanbanEngine.revision` property. The brief (kanban-web-gui-prep O5) defines the revision counter as a per-instance write counter for GUI change-detection. Task #810 (implementation) depends on #809.

**Key finding:** The revision counter is already implemented in `serve/kanban/src/owlbear_kanban/engine.py`. Tests will pass GREEN immediately rather than failing RED. The TDD RED→GREEN sequence across #809/#810 is moot — tests should still be written as regression coverage.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/kanban/src/owlbear_kanban/engine.py` L64–75 | Codebase | 1.0 — `_revision=0` init, `revision` property |
| `engine.py` — mutating methods | Codebase | 1.0 — `_revision += 1` in create, edit, move, claim, release |
| `engine.py` L498–580 — compound ops | Codebase | 1.0 — `start_work` delegates to `claim_task`; `end_work` delegates to multiple ops |
| `tests/test_kanban_engine_crud.py` | Codebase | 0.9 — fixture pattern: `_BASE_CONFIG_YAML`, `kanban_dir`, `engine` |
| `tests/test_engine_package_boundary_817.py` | Codebase | 0.7 — confirms `revision` in `ENGINE_PUBLIC_API` surface |

## 3. Analysis

### Revision Increment Behavior

| Operation | Delegates To | Revision Delta |
|-----------|-------------|----------------|
| `create_task` | — | +1 |
| `edit_task` | — | +1 |
| `move_task` | — | +1 |
| `claim_task` | — | +1 |
| `release_task` | — | +1 |
| `start_work` | `claim_task` | +1 |
| `end_work(success)` | `edit_task` + `release_task` + `move_task` | +3 |
| `end_work(fail)` | `edit_task` + `release_task` | +2 |
| `end_work(block)` | `edit_task` + `edit_task` + `release_task` | +3 |
| `end_work(reject)` | `edit_task` + `release_task` + `move_task` | +3 |

### Test Design

| Test Case | AC | What to Assert |
|-----------|-----|----------------|
| `test_revision_starts_at_zero` | AC1 | Fresh engine → `revision == 0` |
| `test_create_task_increments` | AC2 | `revision` increases by 1 |
| `test_edit_task_increments` | AC2 | `revision` increases by 1 |
| `test_move_task_increments` | AC2 | `revision` increases by 1 |
| `test_claim_task_increments` | AC2 | `revision` increases by 1 |
| `test_release_task_increments` | AC2 | `revision` increases by 1 |
| `test_start_work_increments` | AC2 | `revision` increases (via claim) |
| `test_end_work_increments` | AC2 | `revision` increases (compound) |
| `test_revision_read_only` | AC3 | Setting `engine.revision = X` → `AttributeError` |
| `test_revision_per_instance` | AC4 | Two engines, independent counters |

File: `tests/test_revision_counter_809.py`. Mirrors `test_kanban_engine_crud.py` fixture pattern.

### Implementation Overlap

Task #810 is "Add revision counter" with `depends_on: [809]`, implying RED-first TDD. Since the implementation pre-exists, #810 can be resolved as already-complete once #809 tests pass. Recommend noting this in #810's research.

## 4. Recommendation

Write 10 test cases per the table above. Assert exact deltas for atomic ops; assert `revision > before` for compound ops (makes tests resilient to internal delegation changes). Confidence: **0.92**.

Challenge: FALLBACK — trivial test task, no design trade-offs to challenge.

## 5. Follow-up Tasks

- #809 proceeds to backlog for test implementation (this task)
- #810 research should note implementation pre-exists
