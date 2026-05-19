---
id: 993
title: Emit outcome budget_exceeded from reconcile_tasks for BudgetExceededError
status: archived
priority: needed
created: 2026-03-24T17:03:00.4937075+01:00
updated: 2026-03-24T21:52:42.1657898+01:00
started: 2026-03-24T21:52:19.7113419+01:00
completed: 2026-03-24T21:52:19.7113419+01:00
tags:
    - daemon
    - hooks
    - scope:core
    - type:build
depends_on:
    - 985
class: standard
---

## Acceptance Criteria

- [ ] AC1: In reconcile_tasks (src/owlbear/daemon.py), detect BudgetExceededError before emitting TASK_COMPLETE. Emit outcome: budget_exceeded when isinstance(exc, BudgetExceededError), emit outcome: failure otherwise. Use lazy import matching the pattern at src/owlbear/daemon.py:521.
- [ ] AC2: Non-budget exceptions still emit outcome: failure. Existing test_failure_emits_hook_with_failure_outcome at tests/test_daemon_coverage_gaps.py:749 must stay green.
- [ ] AC3: Successful tasks still emit outcome: success. Existing test_success_emits_hook at tests/test_daemon_coverage_gaps.py:675 must stay green.
- [ ] AC4: Update TaskCompleteData docstring (src/owlbear/core/hooks.py:122) to document valid outcome values: success, failure, budget_exceeded.
- [ ] AC5: All scoped tests pass (RED tests from #995 plus existing reconcile tests in tests/test_daemon_coverage_gaps.py). Ruff clean on changed files.

### Architecture Notes

- Change is approximately 5 LOC in reconcile_tasks plus a docstring update.
- The lazy import of BudgetExceededError already exists inside schedule_task_retry at src/owlbear/daemon.py:521. Add a matching lazy import in the failure branch of reconcile_tasks.
- All 6 TASK_COMPLETE consumers use outcome != success or match: {outcome: failure} patterns. The new budget_exceeded value is naturally excluded from failure-specific rules and correctly included in not-success checks. See docs/research/budget-exceeded-outcome-emission.md section 3.2 for the full consumer audit.
- Domain: bootstrap (daemon.py primary). The TypedDict docstring update in core/hooks.py is ancillary.

## Research

Doc: docs/research/budget-exceeded-outcome-emission.md

[[2026-03-24]] Tue 17:52
Preceding test task: #995. Stale depends_on 985 in frontmatter should be replaced with 995 manually.

[[2026-03-24]] Tue 17:52

## Architecture Review

**Verdict:** APPROVED (via SPLIT)

### AC Assessment

| Original AC | Assessment | Action |
|-------------|------------|--------|
| (1) emit budget_exceeded for BudgetExceededError | Clear, verifiable via mock assertion | Kept as AC1 |
| (2) still emit failure for other exceptions | Clear, already covered by existing test at tests/test_daemon_coverage_gaps.py:749 | Kept as AC2 regression guard |
| (3) existing consumers skip budget_exceeded | Inherent property of != success pattern; verified by research doc section 3.2 consumer audit | Kept as AC3 regression guard (success path) |
| (4) TypedDict docstring updated | Clear, verifiable by reading the docstring | Kept as AC4 |
| (5) test: budget-exceeded outcome | Test requirement, not implementation | Extracted to #995 (test task) |
| (6) test: failure outcome preserved | Already covered by existing test_failure_emits_hook_with_failure_outcome | Dropped as duplicate of AC2 |

### Architecture Notes

- Single domain: bootstrap (daemon.py primary). TypedDict docstring update in core/hooks.py is ancillary, not a domain violation.
- Module layering: correct. daemon.py (assembly layer) imports from core/errors.py (core layer). No upward imports.
- Change scope: approximately 5 LOC in reconcile_tasks plus 1 docstring update. Minimal. KISS.
- Pattern: lazy import of BudgetExceededError matches existing pattern at src/owlbear/daemon.py:521. isinstance check before emit.
- Consumer safety: all 6 TASK_COMPLETE consumers audited in docs/research/budget-exceeded-outcome-emission.md section 3.2. All use outcome != success or match equality on failure. No consumer will break.
- No new system boundaries, no security surface changes.

### Changes Made

- Split: created #995 (Test: budget_exceeded outcome from reconcile_tasks) at todo with 3 AC lines.
- Refined: rewrote #993 body from paragraph to 5 numbered AC lines with file targets and architecture notes.
- Fixed: noted stale depends_on 985 in body (985 is archived via SPLIT; real dep is #995).
- TDD compliance: #995 precedes #993.

### Dependencies

- Stale: depends_on 985 in frontmatter needs manual replacement with 995.
- Test task: #995 precedes this task (TDD RED).
- No downstream tasks depend on #993 currently.

[[2026-03-24]] Tue 17:52

## Architecture Review

**Verdict:** APPROVED (via SPLIT)

### AC Assessment

| Original AC | Assessment | Action |
|-------------|------------|--------|
| (1) emit budget_exceeded for BudgetExceededError | Clear, verifiable via mock assertion | Kept as AC1 |
| (2) still emit failure for other exceptions | Clear, already covered by existing test at tests/test_daemon_coverage_gaps.py:749 | Kept as AC2 regression guard |
| (3) existing consumers skip budget_exceeded | Inherent property of != success pattern; verified by research doc section 3.2 consumer audit | Kept as AC3 regression guard (success path) |
| (4) TypedDict docstring updated | Clear, verifiable by reading the docstring | Kept as AC4 |
| (5) test: budget-exceeded outcome | Test requirement, not implementation | Extracted to #995 (test task) |
| (6) test: failure outcome preserved | Already covered by existing test_failure_emits_hook_with_failure_outcome | Dropped as duplicate of AC2 |

### Architecture Notes

- Single domain: bootstrap (daemon.py primary). TypedDict docstring update in core/hooks.py is ancillary, not a domain violation.
- Module layering: correct. daemon.py (assembly layer) imports from core/errors.py (core layer). No upward imports.
- Change scope: approximately 5 LOC in reconcile_tasks plus 1 docstring update. Minimal. KISS.
- Pattern: lazy import of BudgetExceededError matches existing pattern at src/owlbear/daemon.py:521. isinstance check before emit.
- Consumer safety: all 6 TASK_COMPLETE consumers audited in docs/research/budget-exceeded-outcome-emission.md section 3.2. All use outcome != success or match equality on failure. No consumer will break.
- No new system boundaries, no security surface changes.

### Changes Made

- Split: created #995 (Test: budget_exceeded outcome from reconcile_tasks) at todo with 3 AC lines.
- Refined: rewrote #993 body from paragraph to 5 numbered AC lines with file targets and architecture notes.
- Fixed: noted stale depends_on 985 in body (985 is archived via SPLIT; real dep is #995).
- TDD compliance: #995 precedes #993.

### Dependencies

- Stale: depends_on 985 in frontmatter needs manual replacement with 995.
- Test task: #995 precedes this task (TDD RED).
- No downstream tasks depend on #993 currently.

[[2026-03-24]] Tue 20:18

## Test-Writer Notes

- Test file: tests/test_daemon_coverage_gaps.py
- Classes: TestFromAC_ReconcileBudgetExceededOutcome (committed in #995 test-writer)
- Tests per category: happy 1, edge 0, error 1, boundary 1
- Total: 3 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1 (BudgetExceededError -> outcome budget_exceeded): test_budget_exceeded_emits_hook_with_budget_exceeded_outcome (FAIL)
  AC2 (non-budget -> outcome failure): regression guard test_failure_emits_hook_with_failure_outcome at line 749 (existing, passes)
  AC3 (success -> outcome success): regression guard test_success_emits_hook at line 675 (existing, passes)
  AC4 (docstring update): no test needed - doc-only change
  RED verified: uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_ReconcileBudgetExceededOutcome -v --tb=short -> 3 failed in 1.14s

[[2026-03-24]] Tue 20:57

## Builder Notes

- Files changed: src/owlbear/daemon.py; src/owlbear/core/hooks.py
- Tests: 179 passed in daemon and hook suites; reconcile scope class set also validated (10 passed)
- Coverage: src/owlbear/daemon.py 95%; src/owlbear/core/hooks.py 98%
- Lint: ruff clean on changed files
- Evidence: BudgetExceededError now maps to outcome budget_exceeded in reconcile task-complete emission with lazy import in the failure path; non-budget failure and success regressions remained green.
- Fixes applied: Added lazy import and budget-aware outcome selection in reconcile_tasks; documented valid TaskCompleteData outcome values.

[[2026-03-24]] Tue 21:17

## Review Evidence

### Test Results

- Scoped reconcile pytest: 10 passed, 4 warnings in 2.00s. Warnings were optional dependency skips from tests/conftest.py for qdrant_client.
- Broader daemon and core hooks suite: 179 passed, 4 warnings in 8.42s.
- Coverage from the passing daemon and hooks suite: src/owlbear/daemon.py 95%; src/owlbear/core/hooks.py 98%.

### Lint Results

- ruff check on src/owlbear/daemon.py, src/owlbear/core/hooks.py, and tests/test_daemon_coverage_gaps.py: clean.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| AC1 budget-exceeded outcome mapping | TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_emits_hook_with_budget_exceeded_outcome; TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_not_failure; TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_distinct_from_plain_failure | Yes. The exact payload assertion at tests/test_daemon_coverage_gaps.py:2935 and the side-by-side comparison at tests/test_daemon_coverage_gaps.py:2985 fail if BudgetExceededError still maps to failure or if plain failures map incorrectly. The non-failure assertion at tests/test_daemon_coverage_gaps.py:2959 is broader by itself but is compensated by the stricter companion tests. | COVERED |
| AC2 non-budget exceptions still emit failure | TestFromAC_ReconcileFailureSideEffects::test_failure_emits_hook_with_failure_outcome; TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_distinct_from_plain_failure | Yes. The exact failure payload at tests/test_daemon_coverage_gaps.py:745 and the distinct-outcome comparison at tests/test_daemon_coverage_gaps.py:2985 fail if non-budget exceptions stop mapping to failure. | COVERED |
| AC3 successful tasks still emit success | TestFromAC_ReconcileSuccessPath::test_success_emits_hook | Yes. The exact success payload assertion at tests/test_daemon_coverage_gaps.py:667 fails if the success path regresses. | COVERED |
| AC4 TaskCompleteData docstring documents success, failure, and budget_exceeded | None; doc-only AC | Direct source inspection confirms the docstring at src/owlbear/core/hooks.py:122-128 lists all three valid values. No executable behavior exists to cover with a TestFromAC test. | COVERED |
| AC5 scoped tests pass and changed files are lint clean | Scoped reconcile pytest; passing daemon and hooks suite; task-scoped ruff | Yes. The changed mapping, success regression, failure regression, and file validity are all exercised directly by the passing runs above. | COVERED |

#### Security Review

- No security issues found. The change only classifies an existing exception type and updates docstrings. It adds no new input handling, subprocess use, filesystem access, secret handling, or external calls.

#### Test Integrity

- Builder commit 9dbf37b changed only src/owlbear/daemon.py and src/owlbear/core/hooks.py. It did not touch tests/test_daemon_coverage_gaps.py.
- Current uncommitted changes in tests/test_daemon_coverage_gaps.py only reflow lines in TestFromAC_961 around lines 2873 and 2903. The budget-exceeded tests reviewed here are unchanged.
| Original Test | Change Made | Assessment |
| --- | --- | --- |
| TestFromAC_ReconcileSuccessPath::test_success_emits_hook | No change in builder commit; current method still asserts the exact success payload at tests/test_daemon_coverage_gaps.py:667. | PRESERVED |
| TestFromAC_ReconcileFailureSideEffects::test_failure_emits_hook_with_failure_outcome | No change in builder commit; current method still asserts the exact failure payload at tests/test_daemon_coverage_gaps.py:745. | PRESERVED |
| TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_emits_hook_with_budget_exceeded_outcome | No change in builder commit. Current body matches the original committed intent from b6dbead and still asserts the exact budget_exceeded payload at tests/test_daemon_coverage_gaps.py:2935. | PRESERVED |
| TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_not_failure | No change in builder commit. Current body still asserts that BudgetExceededError does not emit failure at tests/test_daemon_coverage_gaps.py:2959. | PRESERVED |
| TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_distinct_from_plain_failure | No change in builder commit. Current body still checks budget_exceeded for BE3 and failure for FE3 at tests/test_daemon_coverage_gaps.py:2985. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | STRONG | Exact HookEvent.TASK_COMPLETE payload assertions exist for success, failure, and budget_exceeded at tests/test_daemon_coverage_gaps.py:667, :745, and :2935. The distinct-outcome test at :2985 checks both branches in one run. |
| Negative and error paths | STRONG | BudgetExceededError is checked against both exact budget_exceeded behavior and against plain ValueError behavior. Non-budget failure remains covered separately at tests/test_daemon_coverage_gaps.py:745. |
| Mutation reasoning | STRONG | If daemon.py:622 still returned failure for BudgetExceededError, tests at :2935 and :2985 would fail. If it returned budget_exceeded for every exception, tests at :745 and :2985 would fail. If success stopped emitting success, test at :667 would fail. |
| Test independence | STRONG | Each test constructs fresh OrchestratorState, AsyncMock hooks, and task ids; no shared mutable state is reused across tests. |
| Descriptive names | STRONG | The relevant test names describe the scenario and expected outcome directly, including test_budget_exceeded_outcome_distinct_from_plain_failure. |

#### Data Safety

- No data safety issues found. The new code at src/owlbear/daemon.py:620-625 only selects the emitted outcome string before calling the already-existing retry policy. The existing BudgetExceededError retry path at src/owlbear/daemon.py:525-534 still blocks the task and discards the claim.

#### Implementation-Aware Test Gaps

- No significant untested paths. The only new behavioral branch introduced by this task is the exception-type outcome selection at src/owlbear/daemon.py:620-625, and it is covered by exact budget, plain-failure, and success-path tests. The lazy import mirrors the established BudgetExceededError pattern already used in schedule_task_retry at src/owlbear/daemon.py:525.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| AC1 | reconcile_tasks now performs a lazy BudgetExceededError import at src/owlbear/daemon.py:620 and selects budget_exceeded or failure at src/owlbear/daemon.py:622 before emitting HookEvent.TASK_COMPLETE at src/owlbear/daemon.py:624. | tests/test_daemon_coverage_gaps.py:2935; tests/test_daemon_coverage_gaps.py:2959; tests/test_daemon_coverage_gaps.py:2985 | PASS |
| AC2 | Non-budget failures still map to failure through the same conditional at src/owlbear/daemon.py:622. | tests/test_daemon_coverage_gaps.py:745; tests/test_daemon_coverage_gaps.py:2985 | PASS |
| AC3 | Success path still emits success at src/owlbear/daemon.py:643-644. | tests/test_daemon_coverage_gaps.py:667 | PASS |
| AC4 | TaskCompleteData docstring at src/owlbear/core/hooks.py:122-128 documents success, failure, and budget_exceeded. | Source inspection | PASS |
| AC5 | Scoped reconcile pytest passed 10 tests; broader daemon and hooks suite passed 179 tests; task-scoped ruff was clean; daemon.py coverage 95%; core/hooks.py coverage 98%. | Scoped reconcile classes plus daemon and hooks suite | PASS |

### Verdict: PASS

### Action Taken

- kanban\\kanban-md.exe edit 993 -a <review evidence> -t --claim copilot-reviewer
- kanban\\kanban-md.exe edit 993 --status docs --release

[[2026-03-24]] Tue 21:22

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Outcome classification is internal daemon detail captured in docstrings. No new API or convention for the instructions table. |
| 2 | Docstrings | Yes | Pass | TaskCompleteData (hooks.py:122-128) documents success/failure/budget_exceeded. reconcile_tasks (daemon.py:587-596) documents same three outcomes. Both accurate. |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used. Lazy-import mirrors existing internal pattern at daemon.py:525. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc linked | Yes | Pass | docs/research/budget-exceeded-outcome-emission.md exists and linked in task body. Follow-up split to #995. |
| 6 | No impact | N/A | N/A | Items 1-5 evaluated. |

### Files Updated

- None (docstrings correct per AC4 and builder commit)

### Scratch Files Cleaned

- None found (no docs/scratch/993-* files exist)

[[2026-03-24]] Tue 21:52

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 BudgetExceededError outcome | Lazy import at daemon.py:620, isinstance check at :622, emit at :624 | PASS |
| AC2 non-budget failure | else branch at daemon.py:622 emits failure; test_failure_emits_hook_with_failure_outcome green | PASS |
| AC3 success outcome | Success emit at daemon.py:643-644; test_success_emits_hook green | PASS |
| AC4 docstring update | TaskCompleteData docstring at hooks.py:122-128 lists success/failure/budget_exceeded | PASS |
| AC5 tests pass, ruff clean | 10 scoped tests pass; ruff clean on daemon.py, hooks.py, test_daemon_coverage_gaps.py | PASS |

### Test Results

- pytest (scoped): 10 passed in 1.08s
- pytest (full): 4264 passed, 35 pre-existing failures (none related to #993)
- ruff: All checks passed

### AC Quality Score: 5/5

AC was specific, complete, and led to a clean 5-LOC implementation. No improvisation needed by builder or reviewer.

### Confidence: .97

### Action: archive

[[2026-03-24]] Tue 21:52

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 622b722 | chore | kanban/tasks/993-*.md | #993 |
