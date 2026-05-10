---
id: 1415
title: 'E2: Stale test cleanup — delete/archive 219 task-scoped tests from completed
  tasks'
status: todo
priority: important
created: 2026-05-07T23:16:25.317145+00:00
updated: 2026-05-09T20:01:29.510562+00:00
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
- 1478
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
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — no tests applicable.
- All AC lines are (td:0): coordination umbrella, no testable Python interfaces. Work is in subtasks #1463, #1464, #1465.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task — no code changes needed.
- All cleanup execution work was completed in archived subtasks #1463, #1464, and #1465.
- Parent #1415 is coordination closeout only; passing through to review for final validation of aggregate AC evidence.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner skipped. This parent task is a td:0 coordination umbrella, and the failure is established by live filesystem + board-state mismatch before any runtime gate matters.
- Live task-ID test scan found 5 remaining root Python task files in `tests/` and 2 remaining frontend task files in `serve/cockpit/web/src/__tests__/`.

### Lint Results
- Not applicable. No parent-owned implementation diff was provided, and the failing condition is structural.

### Coverage
- N/A for this td:0 coordination closeout.

### Security Review
- No security or data-safety findings in the parent scope.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1: Task-scoped test files for completed/archived tasks identified and removed from `tests/` | Parent contract requires removal at `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md:32`. Live root task-scoped files still present for archived tasks: `tests/test_agent_scope_boundaries_1411.py` (#1411 archived at `.owlbear/kanban/archive/1411-c3-role-boundary-documentation-in-scope-out-of-scope-for-each-agent-skill.md:4`), `tests/test_doc_writer_agent_1424.py` (#1424 archived at `.owlbear/kanban/archive/1424-p1-03-update-doc-writer-agent-md-remove-diagram-responsibility.md:4`), `tests/test_doc_audit_prompt_1425.py` (#1425 archived at `.owlbear/kanban/archive/1425-p1-04-revise-doc-audit-prompt-md-todo-resolution-diagram-ownership.md:4`), and `tests/test_mcp_kanban_merge_1469.py` (#1469 archived at `.owlbear/kanban/archive/1469-e2a-b4-merge-mcp-kanban-task-tests-into-durable.md:4`). | FAIL |
| P2: After cleanup, only tests for active/in-progress tasks remain as task-scoped files | Parent end-state contract is explicit at `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md:33`. Of the 7 remaining task-ID test files, only `tests/test_kanban_topology_1439.py` is still active (`#1439` is `in-progress` at `.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md:4`). The other 6 remaining files map to archived tasks: the 4 root files above plus `serve/cockpit/web/src/__tests__/DetailTab_1380.test.tsx` (#1380 archived at `.owlbear/kanban/archive/1380-p2-05-test-cockpit-task-action-gating-and-confirmations.md:4`) and `serve/cockpit/web/src/__tests__/DetailTab_1381.test.tsx` (#1381 archived at `.owlbear/kanban/archive/1381-p2-06-implement-cockpit-task-action-gating-and-confirmations.md:4`). | FAIL |
| P2: No test coverage regression — overall test pass rate and coverage percentage unchanged or improved after cleanup | The parent body contains no final aggregate runtime evidence beyond the claim that subtask work is complete at `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md:102`. Because the live tree still violates the required end-state, the aggregate post-cleanup gate is not established. | FAIL |
| P3: Verification by counting remaining task-scoped files against board state; running full test suite to confirm no regressions | The counting half of P3 already disproves the closeout: 6 archived-task test files still remain on disk. Parent review therefore cannot certify the final gate. | FAIL |

### Findings
- The parent reached review as a pass-through coordination closeout with no new edits, but its aggregate claim is false on the current board state.
- The frontend child explains part of the mismatch: task #1465 intentionally retained `DetailTab_1380.test.tsx` while `#1381` was still backlog (`.owlbear/kanban/archive/1465-e2c-delete-merge-stale-frontend-tests-44-files-in-serve-cockpit-web-src-tests.md:49`), and later recorded that `DetailTab_1381.test.tsx` had become a separate live task-ID file (`.owlbear/kanban/archive/1465-e2c-delete-merge-stale-frontend-tests-44-files-in-serve-cockpit-web-src-tests.md:294`). That child-level pass does not prove the parent-level final state.
- This is the first review failure on #1415. Loop-breaker rules do not apply yet.

### Deductions
- -0.03: git diff / dirty-tree overlap could not be reconstructed in this review surface. Confidence remains high because the live filesystem + board-state mismatch is direct and sufficient.

### Verdict
- Confidence: 0.97
- FAIL -> backlog
- Rationale: this is a coordination/routing defect, not a builder-local code bug. The parent's stated end-state (only active/in-progress task-ID tests remain) is false in the live workspace.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-baseline #1415 against the current board state and update the parent scope so it covers the remaining archived-task test files still on disk, not just the originally decomposed stale set. | `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md`; `tests/test_agent_scope_boundaries_1411.py`; `tests/test_doc_writer_agent_1424.py`; `tests/test_doc_audit_prompt_1425.py`; `tests/test_mcp_kanban_merge_1469.py`; `serve/cockpit/web/src/__tests__/DetailTab_1380.test.tsx`; `serve/cockpit/web/src/__tests__/DetailTab_1381.test.tsx` | Parent AC requires removal / active-only end-state at lines 32-33, but 6 archived-task files remain on disk. |
| 2 | architect | Decide whether #1415 should spawn a delta cleanup follow-up for the now-archived root/frontend task files or narrow the aggregate closeout contract to a frozen snapshot; in its current wording the task cannot PASS. | `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md`; `.owlbear/kanban/archive/1465-e2c-delete-merge-stale-frontend-tests-44-files-in-serve-cockpit-web-src-tests.md` | Parent closeout claims all work completed at line 102, but child #1465 only justified retaining 1380 while 1381 was still downstream/backlog at line 49; both 1380 and 1381 are now archived. |
[[2026-05-09]]
## Architecture Review (Re-review after reviewer rejection)

### Context
Reviewer rejected #1415 from `review` → `backlog` because 6 stale task-scoped test files remain on disk for archived tasks, violating the parent's aggregate AC. Live re-baseline confirms:

**Stale (archived task, file still on disk):**
- `tests/test_agent_scope_boundaries_1411.py` (#1411 archived)
- `tests/test_doc_writer_agent_1424.py` (#1424 archived)
- `tests/test_doc_audit_prompt_1425.py` (#1425 archived)
- `tests/test_mcp_kanban_merge_1469.py` (#1469 archived)
- `serve/cockpit/web/src/__tests__/DetailTab_1380.test.tsx` (#1380 archived)
- `serve/cockpit/web/src/__tests__/DetailTab_1381.test.tsx` (#1381 archived)

**Active (correctly retained):**
- `tests/test_kanban_topology_1439.py` (#1439 in-progress)
- `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` (#1382 in-progress)

### Decision
Spawned delta cleanup subtask **#1478** (E2-delta: Delete 6 remaining stale task-scoped test files from archived tasks) to cover the gap. Added as dep of #1415. This is the minimal-scope fix: 6 file deletions (with consolidation check) for known-archived tasks.

### Evaluation (re-review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Still one concern: stale test cleanup coordination |
| Interface clarity | PASS | AC unchanged; delta gap covered by #1478 |
| Dependency correctness | PASS | Added #1478 dep — parent cannot close until delta cleanup completes |
| Module layering | N/A | File deletion only |
| TDD compliance | PASS | #1478 gates on full suite pass |
| KISS/YAGNI | PASS | Single follow-up for 6 files, no over-engineering |
| Premise challenge | PASS | Reviewer evidence confirmed real gap |
| Pattern consistency | PASS | Same cleanup pattern as original subtasks |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Test infrastructure only |

### Test Depth
All AC lines: (td:0) — parent is coordination umbrella
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0, coordination umbrella re-approval

### Verdict: APPROVE
- Delta cleanup tracked in #1478 (backlog, parent=#1415)
- Reviewer will verify #1478 completion at next review gate