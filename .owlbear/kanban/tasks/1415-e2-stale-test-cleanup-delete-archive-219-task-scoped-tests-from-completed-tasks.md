---
id: 1415
title: 'E2: Stale test cleanup — delete/archive 219 task-scoped tests from completed
  tasks'
status: todo
priority: important
created: 2026-05-07T23:16:25.317145+00:00
updated: 2026-05-09T04:02:22.117299+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
parent: 1403
depends_on:
- 1410
- 1407
- 1463
- 1464
- 1465
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: Task-scoped test files (`test_*_{task_id}.py`) for completed/archived tasks identified and removed from `tests/`
P2: Before: ~219 stale task-scoped tests in `tests/`. After: only tests for active/in-progress tasks remain as task-scoped files
P2: Valuable test coverage from deleted files consolidated into durable module tests in `serve/*/tests/` per C2 conventions
P2: No test coverage regression — overall test pass rate and coverage percentage unchanged or improved after cleanup
P3: Verification by counting remaining `test_*_{task_id}.py` files in `tests/` against board state; running full test suite to confirm no regressions

## Scope

**In scope:** Stale test identification, deletion, coverage consolidation where warranted
**Out of scope:** Test convention changes (C2), reviewer changes (B1), new test creation beyond consolidation
[[2026-05-09]]
## Research
- Research doc: .owlbear/research/1415-stale-test-cleanup.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Decompose into 3 follow-up tasks by location (root Python 82 files, package-local Python 43 files, frontend TSX 44 files). Start with safe deletes where durable equivalents exist, then rename singles, then merge multi-file groups. (confidence: .85)
- Actual stale count: 169 files (not 219 as estimated)
- Follow-up tasks: #1463 (root), #1464 (pkg-local), #1465 (frontend)
- Challenge: skipped — T1 autonomous cleanup, no architectural decision
[[2026-05-09]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: stale test cleanup. Decomposed by location into #1463, #1464, #1465. |
| Interface clarity | PASS | Parent is coordination umbrella — AC verified against subtask aggregate. Count corrected: 169 stale (not 219). |
| Dependency correctness | PASS | Added subtask deps #1463, #1464, #1465. Original deps #1410, #1407 archived (done). |
| Module layering | N/A | No code changes — file deletion/renaming/merging only. |
| TDD compliance | PASS | Each subtask gates on full suite pass before/after cleanup. |
| KISS/YAGNI | PASS | Mechanical cleanup — no new abstractions. |
| Premise challenge | PASS | 169+ stale files (75K+ lines) is real bloat. Live check found potentially more root files (127 vs research's 84) — subtask ACs may need adjustment at their own reviews. |
| Pattern consistency | PASS | Follows C2 durable test conventions. |
| Security surface | PASS | No new boundaries. |
| Single domain | PASS | Test infrastructure only. |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| P1: Task-scoped files removed | Aggregate of subtasks #1463-1465 | None — verified at subtask completion |
| P2: ~219 stale → only active remain | Research found 169, live check suggests potentially more; exact counts verified per-subtask | Note: subtask reviews will validate counts |
| P2: Coverage consolidated per C2 | Handled by each subtask individually | None |
| P2: No coverage regression | Each subtask runs full suite before/after | None |
| P3: Verification by counting + suite run | Final gate when all subtasks complete | None |

### Test Depth
All AC lines: (td:0) — parent is coordination umbrella, no testable code. Work is in subtasks.
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Reason: Coordination umbrella with no architectural decisions; all work delegated to subtasks

### Design Diverge
- Skipped — no competing approaches; decomposition already performed in research

### Verdict: APPROVE
### Action Taken
- Added `quality` tag for test-writer pass-through (parent produces no testable code)
- Added deps on subtasks #1463, #1464, #1465 (parent completes after subtasks)
- Note: subtask count discrepancy (research 84 root vs live 127) to be resolved at subtask-level reviews
- Subtasks #1463, #1464, #1465 in `research` — will flow through pipeline independently