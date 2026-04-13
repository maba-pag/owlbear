# Tests — Rename TaskRecord → Task

> **Owning task:** #799 — Tests — Rename TaskRecord → Task
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #799 is Phase 1, Chain 1, Step 1 of the kanban engine restructuring (#798). It was scoped to write RED tests verifying:
- AC1: `Task` importable from `engine_models`
- AC2: `TaskRecord` alias resolves to `Task` (object identity)
- AC3: Engine CRUD works with renamed model
- AC4: Tests fail RED before implementation

**Question:** Is this task still actionable, or has later work superseded it?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/kanban/src/owlbear_kanban/models.py` | Codebase | 1.0 — `Task` class definition |
| S2 | `serve/kanban/src/owlbear_kanban/engine.py` | Codebase | 1.0 — All CRUD returns `Task` |
| S3 | `tests/test_kanban_engine_models.py` | Codebase | 1.0 — Existing tests for `Task` model |
| S4 | `tests/test_kanban_engine_crud.py` | Codebase | 1.0 — Existing CRUD tests using `Task` |
| S5 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Design doc | 0.9 — Phasing plan |
| S6 | Task #818 (extract engine) body | Kanban | 0.9 — Phase 2 extraction completed |
| S7 | Task #821 (compat alias removal tests) body | Kanban | 0.9 — Done, alias removal verified |

## 3. Analysis

### AC-by-AC assessment

| AC | Status | Evidence |
|----|--------|----------|
| AC1: `Task` importable from `engine_models` | **Superseded** | `engine_models.py` no longer exists. Renamed to `models.py` in `serve/kanban/` during #818. `Task` importable from `owlbear_kanban.models`. Tests exist in `test_kanban_engine_models.py`. |
| AC2: `TaskRecord` alias → `Task` identity | **Superseded** | Alias was a Phase 1 transition aid. Phase 2 (#818) moved the model and #821/#822 verified+removed the alias. No `TaskRecord` references remain in source code. |
| AC3: Engine CRUD with `Task` | **Superseded** | `test_kanban_engine_crud.py` has 40+ tests covering create, edit, move with `Task`. All pass. |
| AC4: Tests fail RED | **Impossible** | Implementation is complete. Cannot produce failing tests for already-implemented functionality. |

### Dependency chain status

| Task | Title | Status | Notes |
|------|-------|--------|-------|
| #799 | Tests — Rename TaskRecord → Task | research | This task — superseded |
| #800 | Rename TaskRecord → Task with compat alias | research | Implementation counterpart — also superseded |
| #801 | Tests — TaskSummary model | review | Already progressed past #800 dependency |
| #821 | Tests — Compat alias removal | done | Phase 2 — alias removal verified |
| #822 | Remove compat alias + migrate imports | done | Phase 2 — cleanup completed |

The chain (#799 → #800 → #801) was designed for Phase 1 incremental work. Phase 2 extraction (#818) accomplished the rename as part of the broader package move. Downstream tasks (#801+) progressed independently.

## 4. Recommendation

**Archive both #799 and #800 as superseded.** (Confidence: .95)

All four ACs for #799 are either already satisfied by existing tests or structurally impossible (RED tests when GREEN is done). Task #800's implementation is complete in the current codebase.

No new tests needed — existing coverage in `test_kanban_engine_models.py` (28 tests) and `test_kanban_engine_crud.py` (40+ tests) already verifies everything #799 intended.

Challenge: skipped — finding is factual/verifiable (file existence, test counts, task statuses), not opinion-based.

## 5. Follow-up Tasks

None needed. All work has been completed by later tasks in the pipeline.
