---
id: 1415
title: 'E2: Stale test cleanup — delete/archive 219 task-scoped tests from completed
  tasks'
status: archived
priority: medium
created: 2026-05-07T23:16:25.317145+00:00
updated: 2026-05-10T17:12:16.790094+00:00
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

P1: Task-scoped test files (`test_*_{task_id}.py`) for completed/archived tasks identified and removed from `tests/` (td:0)
P2: Before: ~219 stale task-scoped tests in `tests/`. After: only tests for active/in-progress tasks remain as task-scoped files (td:0)
P2: Valuable test coverage from deleted files consolidated into durable module tests in `serve/*/tests/` per C2 conventions (td:0)
P2: No test coverage regression in durable suites that replaced deleted task-scoped files — named durable suites pass and scoped coverage is unchanged or improved (td:0)
P3: Verification by counting remaining `test_*_{task_id}.py` files in `tests/` against board state; running scoped durable suites to confirm no regressions from the cleanup (td:0)

## Scope

**In scope:** Stale test identification, deletion, coverage consolidation where warranted
**Out of scope:** Test convention changes (C2), reviewer changes (B1), new test creation beyond consolidation, branch-wide full-suite green (pre-existing failures unrelated to this cleanup are out of scope)
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
| P2: No test coverage regression — overall test pass rate and coverage percentage unchanged or improved after cleanup | The parent still requires a workspace-wide aggregate gate, but the independent full mixed-suite run on the current head is red (229 Python failures, 10 collection errors). Child `#1478` already documented the same issue and narrowed its analogous regression gate from "full suite passes" to scoped durable suites. Parent `#1415` still retains the broader wording. | FAIL |
| P3: Verification by counting remaining task-scoped files against board state; running full test suite to confirm no regressions | Counting now passes, but the full-suite half is structurally stale for this coordination umbrella: the live workspace still contains active task-scoped work and the mixed-suite branch snapshot is not green. This is a contract defect, not a builder-local miss. | FAIL |

### Findings
- The cleanup end-state is now correct on disk, and the current DetailTab durable suites are green.
- The blocking issue is the parent contract: P2/P3 still demand a branch-wide green/full-suite proof even though child `#1478` already established that this gate must be narrowed to scoped durable suites.
- This is the second review failure on `#1415` (the task file already contains one prior `## Review Evidence` section), so loop-breaker routing applies.

### Deductions
- -0.08: no pre-task baseline snapshot was available for the full mixed-suite run; the fail still stands because the parent AC requires a green aggregate verification that current head cannot provide.
- -0.04: git diff / dirty-tree overlap could not be reconstructed in this tool surface.

### Verdict
- Confidence: 0.88
- FAIL -> backlog
- Rationale: live cleanup state passes, but the parent AC is stale / structurally infeasible. The remaining failure is contract quality, not implementation correctness.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Refine `#1415` P2/P3 so the final regression gate matches the feasible, task-owned evidence surface: current live task-ID scan plus named durable suites, not a branch-wide full mixed-suite green requirement. | `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md`; `.owlbear/kanban/archive/1478-e2-delta-delete-6-remaining-stale-task-scoped-test-files-from-archived-tasks.md` | Parent still requires full-suite verification at AC lines 36-37, while child `#1478` records the reviewer recommendation to narrow to scoped durable suites at line 53 and the architect refinement at line 56. |
| 2 | architect | Re-approve the parent closeout against the refined gate, or explicitly define a baseline-comparison method if a workspace-wide regression claim is still intended despite active/in-progress task-scoped files. | `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md`; `.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md` | Only `tests/test_kanban_topology_1439.py` remains and task `#1439` is still `in-progress`, so the parent's literal "run full test suite to confirm no regressions" wording is not aligned with the live board state. |
[[2026-05-10]]
## Architecture Review (3rd pass — AC contract refinement)

### Context
Second reviewer rejection. Implementation is correct — all stale task-scoped files removed, only `tests/test_kanban_topology_1439.py` (#1439 in-progress) remains. Failure was contract-only: P2/P3 demanded branch-wide full-suite green proof, which is structurally infeasible (229 pre-existing Python failures unrelated to this cleanup).

### AC Changes
| Original AC | Refined AC | Rationale |
|---|---|---|
| P2: "overall test pass rate and coverage percentage unchanged or improved" | P2: "No test coverage regression in durable suites that replaced deleted task-scoped files — named durable suites pass and scoped coverage is unchanged or improved" | Branch-wide green is not task-owned evidence. Child #1478 already applied same narrowing. |
| P3: "running full test suite to confirm no regressions" | P3: "running scoped durable suites to confirm no regressions from the cleanup" | Same rationale. Full-suite red is pre-existing, not caused by cleanup. |
| Scope (out of scope) | Added: "branch-wide full-suite green (pre-existing failures unrelated to this cleanup are out of scope)" | Explicit scope boundary prevents future contract ambiguity. |

### Evaluation (re-review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS | AC now matches feasible evidence surface |
| Dependency correctness | PASS | All deps (#1463, #1464, #1465, #1478) archived/done |
| Module layering | N/A | File deletion only |
| TDD compliance | PASS | Scoped durable suite gate is verifiable |
| KISS/YAGNI | PASS | Minimal AC refinement, no scope expansion |
| Premise challenge | PASS | Reviewer confirmed implementation is correct |
| Pattern consistency | PASS | Matches child #1478's gate narrowing |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Test infrastructure only |

### Test Depth
All AC lines: (td:0) — coordination umbrella, no testable code
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — td:0 contract refinement only

### Verdict: APPROVE (REFINE path — AC tightened, then approved)
[[2026-05-10]]
Architecture Review (3rd pass): REFINE+APPROVE. Refined P2/P3 AC to scope regression gate to durable suites that replaced deleted files, not branch-wide full-suite green (pre-existing 229 Python failures are unrelated to this cleanup). Added explicit out-of-scope boundary. Matches child #1478's already-approved gate narrowing. Implementation is correct — only active task #1439's test file remains. All td:0, test-writer SKIP.
[[2026-05-10]]
## Test-Writer Notes
- Retry cycle — body contains prior `## Test-Writer Notes` and `## Review Evidence`.
- Architecture Review (3rd pass, 2026-05-10) confirms all AC lines are `(td:0)`: coordination umbrella, no testable Python interfaces.
- Required Follow-up items were for the architect (AC contract refinement), now resolved: REFINE+APPROVE verdict appended to task body.
- No new tests required. Reviewer's Required Follow-up contained no missing-test gaps — only contract/AC quality findings addressed by the architect.
- Passing through to builder (coordination closeout only).
[[2026-05-10]]
## Builder Notes
- Non-implementation task (td:0 coordination umbrella) — no code changes required.
- Architecture contract refinement is already resolved in-task (3rd pass REFINE+APPROVE), and test-writer explicitly marked pass-through.
- Implementation evidence lives in archived subtasks (#1463, #1464, #1465, #1478); parent #1415 remains closeout-only.
- Routing to review for final validation against refined AC gate.
[[2026-05-10]]
## Review Evidence
### Test Results
- quality-runner skipped. This is a td:0 coordination umbrella, and the blocking defect is established by live filesystem + board-state mismatch before any runtime gate matters.
- Live task-ID scans:
  - `tests/test_*_[0-9]*.py` -> `tests/test_kanban_topology_1439.py`
  - `serve/*/tests/test_*_[0-9]*.py` -> no matches
  - `serve/cockpit/web/src/__tests__/*_[0-9]*.test.tsx` -> `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`

### Lint Results
- Not run. No parent-owned implementation delta; failing condition is aggregate stale-file state, not source/lint behavior.

### Coverage
- N/A for this td:0 coordination closeout.

### Security Review
- No security or data-safety findings in the parent scope.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1: Task-scoped test files (`test_*_{task_id}.py`) for completed/archived tasks identified and removed from `tests/` | Live root scan leaves only `tests/test_kanban_topology_1439.py`, and task `#1439` is still `in-progress` at `.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md:4`. | PASS |
| P2: Before: ~219 stale task-scoped tests in `tests/`. After: only tests for active/in-progress tasks remain as task-scoped files | Live frontend scan still finds `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`, whose header identifies task `#1382` at line 2, while `.owlbear/kanban/archive/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md:4` marks that task archived. Parent `#1415` still requires this end-state at `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md:34`. | FAIL |
| P2: Valuable test coverage from deleted files consolidated into durable module tests in `serve/*/tests/` per C2 conventions | No new contrary evidence. Archived child `#1464` still records that no `serve/*/tests/test_*_[0-9]*.py` files remain and the durable package-local targets contain the merged coverage at `.owlbear/kanban/archive/1464-e2b-delete-merge-stale-package-local-python-tests-43-files-in-serve-tests.md:164-166`. | PASS |
| P2: No test coverage regression in durable suites that replaced deleted task-scoped files — named durable suites pass and scoped coverage is unchanged or improved | No new contrary evidence on the already-cleaned child surfaces. Archived child `#1464` still records green package-local reruns at `.owlbear/kanban/archive/1464-e2b-delete-merge-stale-package-local-python-tests-43-files-in-serve-tests.md:166`, and archived child `#1465` still records the frontend cleanup gate at 1216 passed / 9 skipped / 0 failed at `.owlbear/kanban/archive/1465-e2c-delete-merge-stale-frontend-tests-44-files-in-serve-cockpit-web-src-tests.md:181-182`. | PASS |
| P3: Verification by counting remaining `test_*_{task_id}.py` files in `tests/` against board state; running scoped durable suites to confirm no regressions from the cleanup | The root `tests/` count still matches the active exception `#1439`, but the parent closeout evidence is stale: child `#1478` and the parent's latest Architecture Review still treat `DetailTab_1382.test.tsx` as an active exception (`.owlbear/kanban/archive/1478-e2-delta-delete-6-remaining-stale-task-scoped-test-files-from-archived-tasks.md:33`, `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md:183`), which is no longer true once `#1382` is archived. The parent's final verification therefore does not match the live board state. | FAIL |

### Findings
- The aggregate cleanup end-state regressed after the earlier child passes: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` now counts as stale because task `#1382` is archived. The parent cannot close while that task-scoped frontend file remains.
- The latest inherited evidence is stale rather than merely incomplete. Child `#1478` still calls `DetailTab_1382.test.tsx` an active exception at `.owlbear/kanban/archive/1478-e2-delta-delete-6-remaining-stale-task-scoped-test-files-from-archived-tasks.md:33`, and parent `#1415` repeats the "only #1439 remains" claim at `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md:183`.

### Deductions
- -0.03: dirty-tree / commit-diff contamination checks were unavailable in this review surface.
- -0.02: durable-suite reruns were not repeated in this cycle because the live board-state mismatch already blocks the td:0 closeout.

### Verdict
- Confidence: 0.88
- FAIL -> backlog
- Rationale: the aggregate stale-test cleanup parent is stale again on live board state. A remaining task-scoped frontend file belongs to archived task `#1382`, so the parent end-state contract is no longer satisfied.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-scan live task-ID test files against current board state and create/refine a delta cleanup task for `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`, including the usual consolidation/retention decision before deletion. | `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx`; `.owlbear/kanban/archive/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md`; `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md` | The live file still exists, its header ties it to `#1382`, and `#1382` is archived, which violates parent P2 at line 34. |
| 2 | architect | Refresh the parent closeout evidence after the delta task lands; do not rely on the current "only #1439 remains" narrative. | `.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md`; `.owlbear/kanban/archive/1478-e2-delta-delete-6-remaining-stale-task-scoped-test-files-from-archived-tasks.md` | Parent line 183 and child line 33 still treat `DetailTab_1382.test.tsx` as an active exception, but `.owlbear/kanban/archive/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md:4` shows the task is archived. |
[[2026-05-10]]

## Architecture Review (4th pass — final stale file)

### Context
Third reviewer rejection. Root cleanup is complete (only active #1439 remains). One stale frontend file discovered: `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` — task #1382 is archived. File contains 23 real conflict-resolution tests from a completed feature (#1382/#1383 both archived, GREEN coverage). Correct disposition: rename to durable naming `DetailTab.conflict-resolution.test.tsx`.

### AC Changes
| Original AC | Refined AC | Rationale |
|---|---|---|
| P1 (unchanged) | P1: Task-scoped test files (`test_*_{task_id}.py` and `*_{task_id}.test.tsx`) for completed/archived tasks identified and removed from `tests/` and `serve/cockpit/web/src/__tests__/` | Explicit frontend path inclusion — was implied but ambiguous |
| (new) | P1b: `DetailTab_1382.test.tsx` renamed to `DetailTab.conflict-resolution.test.tsx` (durable naming, coverage preserved) (td:0) | Single remaining stale file; coverage is real (23 GREEN tests from completed #1382/#1383); retain via rename |

### Evaluation (re-review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Still one concern: stale test cleanup |
| Interface clarity | PASS | AC now explicitly names the remaining file and its disposition |
| Dependency correctness | PASS | All subtask deps (#1463, #1464, #1465, #1478) are archived/done |
| Module layering | N/A | File rename only |
| TDD compliance | PASS | td:0 mechanical rename — no test needed |
| KISS/YAGNI | PASS | Single rename in parent closeout avoids another full pipeline cycle for 1 file |
| Premise challenge | PASS | File confirmed stale via live board scan |
| Pattern consistency | PASS | Durable naming matches C2 conventions (`DetailTab.{topic}.test.tsx` pattern) |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Test infrastructure only |

### Test Depth
All AC lines: (td:0) — mechanical file rename, no testable code
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — td:0 single-file rename

### Verdict: APPROVE (REFINE path — AC tightened to cover last stale file, then approved)
- Remaining builder work: rename `DetailTab_1382.test.tsx` → `DetailTab.conflict-resolution.test.tsx`, verify tests still pass
- No new subtask needed — single rename is builder-trivial in parent closeout
[[2026-05-10]]
Architecture Review (4th pass): REFINE+APPROVE. Refined P1 to explicitly cover frontend task-scoped files. Added P1b: rename `DetailTab_1382.test.tsx` → `DetailTab.conflict-resolution.test.tsx` (23 GREEN tests from completed #1382/#1383 — retain coverage via durable naming). All td:0, test-writer SKIP. Builder work: single file rename + verify tests pass.
[[2026-05-10]]
## Test-Writer Notes
- Retry cycle (4th pass) — body contains prior `## Test-Writer Notes` and `## Review Evidence` sections.
- Architecture Review (4th pass, 2026-05-10) confirms all AC lines are `(td:0)`: coordination umbrella, no testable code. Test-writer: SKIP.
- Required Follow-up items in latest Review Evidence were for the architect (re-scan stale frontend file, create delta cleanup task for `DetailTab_1382.test.tsx`). Both resolved: 4th Architecture Review REFINE+APPROVE covers the disposition (rename to durable naming `DetailTab.conflict-resolution.test.tsx`).
- No new tests required. Passing through to builder (single file rename in parent closeout).
[[2026-05-10]]
## Builder Notes
- Implementation: renamed `serve/cockpit/web/src/__tests__/DetailTab_1382.test.tsx` to `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx` (durable naming per AC P1b).
- Tests: scoped quality-runner on renamed suite passed (`23 passed, 0 failed, 0 skipped`).
- Coverage: N/A for this td:0 mechanical rename task (quality-runner frontend scoped run does not report coverage in this mode).
- Lint: clean (`eslint: 0`).
- Evidence summary: stale task-scoped filename tied to archived task `#1382` removed; durable replacement file now present under non-task-scoped naming.
- Commit: `aafafb9d` (`chore: rename stale DetailTab task-scoped test (#1415, builder)`).
- Approach: surgical single-file rename with scoped frontend verification only; no test-content changes.
[[2026-05-10]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run on [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx): 23 passed, 0 failed, 0 skipped. Exit codes: vitest=0, eslint=0.
- VS Code diagnostics: no errors in [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx).
- Live pattern check: `tests/test_*_[0-9]*.py` returned [tests/test_kanban_topology_1439.py](tests/test_kanban_topology_1439.py) only.
- Live pattern check: `serve/*/tests/test_*_[0-9]*.py` returned no matches.
- Live pattern check: `serve/cockpit/web/src/__tests__/*_[0-9]*.test.tsx` returned no matches.

### Lint Results
- ESLint clean for [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx). No violations reported.

### Coverage
- N/A for this td:0 coordination closeout.
- Inherited durable-suite evidence remains accepted from archived child reviews: [#1464](.owlbear/kanban/archive/1464-e2b-delete-merge-stale-package-local-python-tests-43-files-in-serve-tests.md#L166) independently reran the package-local suites and passed; [#1465](.owlbear/kanban/archive/1465-e2c-delete-merge-stale-frontend-tests-44-files-in-serve-cockpit-web-src-tests.md#L304) accepted the frontend durable-suite gate under the architect-refined fallback.

### Security Review
- No security or data-safety findings. Scope is mechanical test-file cleanup and rename only.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1: Task-scoped test files for completed/archived tasks identified and removed from `tests/` | Live root scan leaves only [tests/test_kanban_topology_1439.py](tests/test_kanban_topology_1439.py), and [#1439](.owlbear/kanban/tasks/1439-p4-02-collapse-kanban-engine-topology-into-product-constants.md#L4) is still `in-progress`. | PASS |
| P1b: `DetailTab_1382.test.tsx` renamed to `DetailTab.conflict-resolution.test.tsx` (4th-pass refinement) | The latest binding refinement adds P1b at [#1415](.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md#L253) and re-approves it at [#1415](.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md#L280). Builder recorded the rename at [#1415](.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md#L289) and the builder commit at [#1415](.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md#L294). The old `DetailTab_1382.test.tsx` path is absent on disk, the durable path [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx) exists, and [#1382](.owlbear/kanban/archive/1382-p2-07-test-cockpit-task-conflict-resolution-workflow.md#L4) is archived. | PASS |
| P2: After cleanup, only tests for active/in-progress tasks remain as task-scoped files | Live workspace scan now returns one active root task-scoped file, no package-local task-scoped Python files, and no frontend task-scoped TSX files. | PASS |
| P2: Valuable test coverage from deleted files consolidated into durable module tests | Archived child [#1464](.owlbear/kanban/archive/1464-e2b-delete-merge-stale-package-local-python-tests-43-files-in-serve-tests.md#L166) independently verified the package-local consolidation suites; archived child [#1465](.owlbear/kanban/archive/1465-e2c-delete-merge-stale-frontend-tests-44-files-in-serve-cockpit-web-src-tests.md#L304) independently accepted the frontend durable-suite gate. | PASS |
| P2/P3: No regression in durable suites and scoped durable suites confirm the cleanup | Current independent run of [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx) is green (23 passed, 0 failed, 0 skipped), satisfying the 4th-pass requirement to rename the durable suite and verify it still passes. | PASS |

### Findings
- No blocking findings.
- The verdict is anchored to the latest binding Architecture Review refinement at [#1415](.owlbear/kanban/tasks/1415-e2-stale-test-cleanup-delete-archive-219-task-scoped-tests-from-completed-tasks.md#L280), not the stale earlier AC wording at the top of the task file.

### Deductions
- -0.04: exact `git diff` / `git status` proof for commit `aafafb9d` was unavailable in-session, and HEAD has advanced since that commit. Rename purity is therefore inferred from board notes, git-log presence, file absence/presence, and green scoped verification rather than direct diff output.
- -0.03: the top Acceptance Criteria block was not rewritten after the 4th-pass refinement, so this review relies on the later binding Architecture Review section.

### Verdict
- Confidence: 0.93
- PASS -> docs
- Rationale: the final stale frontend task-scoped file was converted to durable naming, the old task-scoped path is gone, the renamed suite passes independently, and live task-ID scans now show only the active [tests/test_kanban_topology_1439.py](tests/test_kanban_topology_1439.py) exception at the root.
[[2026-05-10]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task is mechanical test-file cleanup/rename only. No behavior, API, CLI, config, or package structure changed. No IN-scope prose docs reference test file paths. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified — only test files deleted/renamed. |
| 3 | External attribution | No | N/A | No external patterns cited in task or research doc. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1415-stale-test-cleanup.md` exists and is linked from the task body. Follow-up tasks #1463, #1464, #1465 were created as documented. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matches the renamed `DetailTab.conflict-resolution.test.tsx`. Footer updated to `Last verified: 2026-05-10 (28e32840)`. Committed as `75c51747`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | Deleted files are task-scoped test files only. No IN-scope descriptive docs reference deleted test files. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx` (renamed from `DetailTab_1382.test.tsx`) | OUT (test file) | N/A — diagram footer updated for `describes` match |
| `tests/test_kanban_topology_1439.py` (active, retained) | OUT (test file) | N/A |
| `.owlbear/research/1415-stale-test-cleanup.md` | IN (research doc) | Verified — exists and linked |
| `share/diagrams/cockpit.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer stamp updated (commit `75c51747`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1415-*` files found)
[[2026-05-10]]
## Audit
### Regression Detection
- quality-runner mode full: Python 4372 passed / 224 failed / 10 errors (all pre-existing, unrelated to cleanup scope per explicit out-of-scope clause); Frontend 1217 passed / 0 failed / 9 skipped; ESLint 1 pre-existing rule-config error; Ruff 290 pre-existing issues
- regression verdict: PASS (no new regressions attributable to this task)

### Intent Verification
- scope alignment: PASS (changes limited to test infrastructure: 1 stale test file renamed to durable naming, 1 diagram footer updated)
- purpose match: PASS (stale task-scoped test files removed/renamed for completed tasks; only active task #1439's test file remains)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC required 4 architecture passes and 3 reviewer cycles to stabilize. Initial AC overclaimed (branch-wide full-suite green requirement), and frontend task-scoped file paths were initially omitted from P1 scope. Self-corrected through iteration; final AC (4th pass) is specific and verifiable. Score reflects the notable gaps that required significant rework cycles.

### Commit Integrity
- upstream commit presence: PASS (builder commit aafafb9d "chore: rename stale DetailTab task-scoped test (#1415, builder)" confirmed via git log; doc-writer commit 75c51747 "docs: update cockpit diagram footer for #1415 (doc-writer)" confirmed)
- kanban commit packaging: pending (this audit)

### Deduction Breakdown
- AC quality score 3/5: -.03
### Confidence: .97
### Action: archive