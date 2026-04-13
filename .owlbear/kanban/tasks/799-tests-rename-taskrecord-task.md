---
id: 799
title: Tests — Rename TaskRecord → Task
status: research
priority: critical
created: '2026-04-10T21:20:28.162627+00:00'
updated: '2026-04-12T23:58:59.935701+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Test file verifies `Task` importable from `engine_models`
- Verifies `TaskRecord` alias resolves to `Task` (same object identity)
- Verifies engine CRUD works with renamed model (create, edit, move, show, list)
- Tests fail RED before implementation

## Context

Phase 1, Chain 1 step 1. First task in the model cleanup chain.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/799-rename-taskrecord-task-tests.md
- Sources: 7 studied, 7 high-relevance (all codebase/kanban)
- Recommendation: Archive #799 and #800 as superseded (confidence: .95)
- Rationale: Phase 2 extraction (#818) renamed `engine_models.py` → `models.py`, `TaskRecord` → `Task`, and moved to `serve/kanban/`. Existing tests (`test_kanban_engine_models.py`, `test_kanban_engine_crud.py`) already verify all four ACs. RED tests impossible — implementation is complete.
- Tier: T1 (autonomous cleanup)
- Follow-up tasks created: none
- Decision requests: none
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Task is superseded — evaluation moot |
| Interface clarity | N/A | Superseded |
| Dependency correctness | N/A | Superseded |
| Module layering | N/A | Superseded |
| TDD compliance | FAIL | RED tests impossible — implementation complete |
| KISS/YAGNI | N/A | Superseded |
| Premise challenge | **FAIL** | Task's premise no longer holds. `engine_models.py` no longer exists; `Task` is canonical in `owlbear_kanban.models`; `TaskRecord` alias was created and removed in Phase 2. All four ACs are either already covered or structurally impossible. |
| Pattern consistency | N/A | Superseded |
| Security surface | N/A | No new boundaries |
| Single domain | N/A | Superseded |

### Codebase Evidence

1. **`Task` class** — defined at `serve/kanban/src/owlbear_kanban/models.py:60-87`, canonical import path `owlbear_kanban.models`
2. **`engine_models.py`** — does not exist anywhere in the codebase (file_search: 0 results)
3. **`TaskRecord` references** — zero remaining in `serve/**/*.py`; only in `test_compat_alias_removal_821.py` (intentional, self-excluded) and `.owlbear/` docs
4. **Existing test coverage** — `test_kanban_engine_models.py` (28 tests, imports `Task` from `owlbear_kanban.models`), `test_kanban_engine_crud.py` (40+ tests using `Task` for create/edit/move/show/list)
5. **Superseding tasks** — #818 (extract engine, renamed model), #821 (compat alias removal tests, done), #822 (remove compat alias + migrate imports, done)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test `Task` importable from `engine_models` | SUPERSEDED — `engine_models` no longer exists; `Task` importable from `owlbear_kanban.models`; verified by existing tests | None possible |
| `TaskRecord` alias resolves to `Task` | SUPERSEDED — alias was created (#800 scope) and removed (#822) in Phase 2; both transitions complete | None possible |
| Engine CRUD works with renamed model | SUPERSEDED — `test_kanban_engine_crud.py` has 40+ tests exercising create, edit, move, show, list with `Task` | None possible |
| Tests fail RED before implementation | IMPOSSIBLE — implementation is complete; cannot produce failing tests for working code | None possible |

### Challenge Results
- Challenger: SKIPPED (REJECT verdict — not required)

### Verdict: REJECT
### Action Taken: Rejected to research. All four ACs are satisfied by existing tests or structurally impossible (RED for completed work). Phase 2 extraction (#818) and alias cleanup (#821/#822) superseded this Phase 1 task entirely. **Recommend archival** — no further work needed. Task #800 (implementation counterpart, already at research) should also be archived for the same reason.
[[2026-04-12]]
## Research (validation pass)

Previous research doc validated against current codebase — all findings hold.

### Verification

| Evidence point | Status |
|---|---|
| `engine_models.py` absent | Confirmed (file_search: 0 results) |
| `TaskRecord` absent in `serve/**/*.py` | Confirmed (grep: 0 matches) |
| `Task` canonical at `owlbear_kanban.models:58` | Confirmed |
| `test_kanban_engine_models.py` exists (28 tests) | Confirmed |
| `test_kanban_engine_crud.py` exists (40+ tests) | Confirmed |
| #800 at research, unclaimed | Confirmed |

### Recommendation: Archive #799 and #800 as superseded (confidence: .95)

All four ACs are satisfied by existing tests or structurally impossible. Phase 2 extraction (#818) and alias cleanup (#821/#822) completed the work this task intended. No follow-up tasks needed. No decision requests.

Tier: T1 (autonomous cleanup — archival of superseded tasks)

Challenge: SKIPPED — validation pass of factual findings, no opinion-based recommendation
[[2026-04-12]]
## Architecture Review (2nd pass — terminal)

### Verdict: REJECT → ARCHIVE RECOMMENDED

This is the second architecture review. The prior cycle (REJECT → research validation → backlog) confirmed all findings. Independent codebase verification this pass re-confirms:

| Evidence Point | Status |
|---|---|
| `engine_models.py` exists | **No** — 0 files found |
| `TaskRecord` in `serve/**/*.py` | **0 matches** |
| `Task` canonical at `owlbear_kanban.models:58` | **Confirmed** |
| `test_kanban_engine_models.py` exists | **Confirmed** |
| `test_kanban_engine_crud.py` exists | **Confirmed** |

### AC Assessment (unchanged)

| AC Line | Status |
|---|---|
| `Task` importable from `engine_models` | SUPERSEDED — `engine_models` doesn't exist; `Task` importable from `owlbear_kanban.models` |
| `TaskRecord` alias resolves to `Task` | SUPERSEDED — alias created and removed in Phase 2 (#822) |
| Engine CRUD works with renamed model | SUPERSEDED — 40+ tests in `test_kanban_engine_crud.py` |
| Tests fail RED before implementation | IMPOSSIBLE — implementation complete |

### Premise Challenge: FAIL
Task premise invalid. The rename this task tests for was completed by #818 (extract engine) and cleaned up by #821/#822 (alias removal). All AC items are covered or structurally impossible.

### Challenge: SKIPPED (REJECT verdict)

### Action: TERMINAL REJECT — ARCHIVE THIS TASK
This task has completed two full review cycles with identical findings. No amount of further research will change the structural reality: the work is done, the old module doesn't exist, and RED tests are impossible for completed implementations. **Orchestrator should archive #799 and #800 (implementation counterpart) rather than re-processing.** No follow-up tasks needed.