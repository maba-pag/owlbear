---
id: 956
title: Reuse daemon retry state for task-scoped HookReaction retries
status: archived
priority: important
created: 2026-03-23T03:22:48.5688469+01:00
updated: 2026-03-25T10:48:31.7100453+01:00
started: 2026-03-25T10:48:26.7630527+01:00
completed: 2026-03-25T10:48:26.7630527+01:00
tags:
    - agent
    - hooks
    - daemon
    - scope:core
    - type:build
parent: 950
depends_on:
    - 955
class: standard
---

Board governance task â€” work decomposed into #984 and #985 by researcher. This task is complete when both children are archived.

## AC

- [ ] #984 (Extract schedule_task_retry from reconcile_tasks) is archived.
- [ ] #985 (Wire real retry executor into HookReactionRouter) is archived.
- [ ] Together, they fulfill the original mandate: task-scoped failure reactions delegate to the existing retry scheduler and block-on-exhaustion path, honoring task_retry_max_attempts and backoff settings.
- [ ] No src/ or tests/ changes from this governance task itself.

See docs/research/hook-reaction-retry-delegation.md for the full design (Option A: extract + mutable dict, .85 confidence).

[[2026-03-24]] Tue 04:38

## Architecture Review

**Verdict:** APPROVED (governance parent)

### AC Assessment

| AC Line | Assessment | Action |

| --- | --- | --- |

| #984 is archived | Verifiable terminal state | Keep |

| #985 is archived | Verifiable terminal state | Keep |

| Together fulfill original retry-delegation mandate | Verifiable via #984 + #985 AC compliance | Keep |

| No src/tests changes from this task | Governance boundary | Keep |

### Architecture Notes

- Research doc (docs/research/hook-reaction-retry-delegation.md) recommends Option A: extract schedule_task_retry + mutable dict late-binding (.85 confidence). Architecturally sound:

  - schedule_task_retry stays in daemon.py (assembly layer) — no module layering violation

  - Router `_executors` dict at src/owlbear/core/hook_reaction_router.py:55 is mutable by design; late-binding via dict replacement is the simplest correct approach

  - Idempotent scheduling (same-or-higher attempt guard) prevents double-retry when both reconcile_tasks and hook reaction fire on the same failure

  - OrchestratorState.retries at src/owlbear/daemon.py:118 remains the single source of truth for retry state

- No TDD predecessor needed for this governance task; #984 and #985 require their own TDD pairs when reviewed individually

- Dependency #955 is in docs status (nearly done) — no blocker for children

### Changes Made

- Rewrote #956 body as governance-only parent (decomposition already done by researcher)

- Set parent: 956 on #984 and #985

- Preserved research section from earlier append

### Dependencies

- Verified: #955 (docs status, nearly done)

- Children: #984 (backlog, depends_on 955), #985 (ideation, depends_on 984)

- Parent #950 archived — closure note references #956 as retry-reuse carrier

[[2026-03-24]] Tue 05:22

## Test-Writer Notes

- Non-implementation task (governance parent) — no tests applicable.

- AC explicitly states: 'No src/ or tests/ changes from this governance task itself.'

[[2026-03-24]] Tue 09:40

## Builder Notes

- Non-implementation task - no code changes needed.
- Passing through to review.

[[2026-03-24]] Tue 10:08

## Review Evidence

## Review: #956 - Reuse daemon retry state for task-scoped HookReaction retries

### Scope

- Governance parent task; no direct src/ or tests/ changes are expected from #956 itself.
- Review verified both child-task state and current runtime/source evidence for the delegated-retry mandate.
- Final pytest evidence below comes from isolated background terminal runs after one contradictory foreground run was discarded as unreliable.

### Test Results

- `uv run pytest tests/test_schedule_task_retry.py -q --tb=short` -> 30 passed, 2 warnings.
- `uv run pytest tests/test_955_hook_reaction_schema_bootstrap.py::TestFromAC_955_BuildHooksReturnContract::test_build_hooks_noop_executors_do_not_raise_on_emit -q --tb=short` -> 1 passed, 2 warnings.
- Warnings were the standard optional-dependency skips from `tests/conftest.py` for missing `qdrant_client`; unrelated to this task.

### Lint Results

- `uv run ruff check src/owlbear/daemon.py src/owlbear/bootstrap/hooks.py tests/test_schedule_task_retry.py tests/test_955_hook_reaction_schema_bootstrap.py` -> All checks passed.

### Test-Writer Coverage

- N/A for the parent governance task: #956 has no task-owned `TestFromAC_*` classes.
- Child #984's dedicated RED/GREEN file `tests/test_schedule_task_retry.py` currently passes, which confirms only the extraction half of the parent mandate.

### TestFromAC Comparison

- N/A for #956 itself. The builder notes for #956 state this was a non-implementation pass-through with no code/test edits.

### AC Compliance

| AC Line | Evidence | Status |
| --- | --- | --- |
| AC1: `#984` is archived | `kanban\kanban-md.exe show 984` reports `status: archived` and `Claimed by: builder` | FAIL |
| AC2: `#985` is archived | `kanban\kanban-md.exe show 985` reports `status: archived` | FAIL |
| AC3: original retry-delegation mandate is fulfilled together | First half is present: `src/owlbear/daemon.py:506` defines `schedule_task_retry`, `src/owlbear/daemon.py:615` shows `reconcile_tasks()` delegates to it, and `tests/test_schedule_task_retry.py` passes 30/30. Second half is not done: `src/owlbear/bootstrap/hooks.py:65` still wires `executors={notify: _noop, retry: _noop, escalate: _noop}`, and a workspace search found no `make_retry_executor` symbol under `src/owlbear/**/*.py`. The current bootstrap test `tests/test_955_hook_reaction_schema_bootstrap.py::TestFromAC_955_BuildHooksReturnContract::test_build_hooks_noop_executors_do_not_raise_on_emit` still passes against noop behavior. | FAIL |
| AC4: no `src/` or `tests/` changes from this governance task itself | `kanban\kanban-md.exe show 956` -> Builder Notes: `Non-implementation task - no code changes needed.` No direct #956-owned code/test changes were presented in review. | PASS |

### Security / Data Safety

- No security or data-safety findings in the reviewed current source surface.
- Rejection is for incompleteness / premature routing, not for a vulnerability.

### Verdict

- FAIL
- Confidence: .97
- Reason: #956 reached review prematurely. Child #984 is not archived, child #985 has not left ideation, and the hook bootstrap path still uses a noop retry executor, so the parent governance task is not complete.

[[2026-03-24]] Tue 11:22

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about governance prerequisites (child #984 and #985 not archived), not missing tests.
- This is a governance-only parent task. AC explicitly states: 'No src/ or tests/ changes from this governance task itself.'
- Existing test-writer pass-through note preserved. Builder will address reviewer findings (child tasks must reach archived).

[[2026-03-24]] Tue 14:56

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task)
- Coverage: N/A
- Lint: N/A
- Evidence: Child prerequisites unresolved (task #984 status todo, task #985 status ideation); #956 AC requires both child tasks archived.
- Fixes applied: None. Blocked pending child completion and archival.

[[2026-03-24]] Tue 15:33

## Test-Writer Notes (retry 2)

- Retry reason: reviewer FAIL was about governance prerequisites (child tasks not archived), not missing tests.
- Task AC explicitly states: 'No src/ or tests/ changes from this governance task itself.'
- Child #984 is in-progress; child #985 is in ideation. Neither is archived.
- Passing through unchanged. Builder must wait for child tasks to complete.

[[2026-03-24]] Tue 17:05

## Builder Notes

- Files changed: none
- Tests: N/A (governance-only parent task)
- Coverage: N/A
- Lint: N/A
- Evidence: task #984 is archived; task #985 is backlog and not archived; parent AC requires both child tasks archived.
- Fixes applied: None. No src or tests changes allowed for this governance task.

[[2026-03-24]] Tue 17:38

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about AC compliance (children #984 and #985 not archived), not missing tests.
- Governance parent, no implementation. Existing notes preserved.
- Builder will address by verifying child task completion.

[[2026-03-24]] Tue 18:17

## Builder Notes

- Files changed: none.
- Tests: N/A (governance parent task; non-implementation).
- Coverage: N/A.
- Lint: N/A.
- Evidence: child task 984 is archived and child task 985 is archived; AC for 956 also forbids src or tests edits.
- Fixes applied: None.

[[2026-03-24]] Tue 20:18

## Review Evidence

## Review: #956 - Reuse daemon retry state for task-scoped HookReaction retries

### Findings

- FAIL: AC3 is still unmet. Task #985 is archived only because it was split into #991, #992, and #993, and those successor tasks are still open.
- The reviewed source still emits outcome failure for BudgetExceededError in src/owlbear/daemon.py:613, and the retry-executor factory and daemon wiring are still absent from src.

### Test Results

- Scoped pytest slice across tests/test_schedule_task_retry.py, tests/test_daemon_coverage_gaps.py, tests/test_955_hook_reaction_schema_bootstrap.py, and tests/test_hook_reaction_router.py reported 188 passed, 3 failed, 4 warnings.
- All three failures are in TestFromAC_ReconcileBudgetExceededOutcome in tests/test_daemon_coverage_gaps.py and show BudgetExceededError still emits outcome failure instead of budget_exceeded.

### Lint Results

- Task-scoped ruff on src/owlbear/daemon.py, src/owlbear/bootstrap/hooks.py, src/owlbear/core/hooks.py, and the reviewed tests reported All checks passed.

### Coverage

- N/A for this governance parent. #956 owns no source or test files.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- N/A for #956 itself. This governance parent has no task-owned TestFromAC classes.

#### Security Review

- No security issues found on the reviewed source surface.

#### Test Integrity

- N/A for #956 itself.

#### Test Quality

- N/A for #956 itself.

#### Data Safety

- No new data-safety issue attributable to #956. Rejection is for incomplete mandate fulfillment.

#### Implementation-Aware Test Gaps

- Successor work is still incomplete. kanban/tasks/991-expose-reaction-executors-dict-from-build-hooks.md:4 is in-progress, kanban/tasks/992-implement-make-retry-executor-and-wire-into-run.md:4 is ideation, and kanban/tasks/993-emit-outcome-budget-exceeded-from-reconcile-tasks.md:4 is todo.
- Current source has only the reaction_executors exposure pieces: src/owlbear/core/hooks.py:179 defines HookRegistry.reaction_executors and src/owlbear/bootstrap/hooks.py:69 stores the noop executors dict on hooks.
- Workspace search found no make_retry_executor symbol in src, and src/owlbear/daemon.py:613 still emits outcome failure for task failures. The three failing budget_exceeded tests confirm that the remaining retry-delegation path is not finished.

### AC Compliance

`| AC Line`| Evidence `| Mapped Test`| Status `|
`| --- `| ---`| --- `| ---`|
`| AC1: #984 is archived`| kanban/tasks/984-extract-schedule-task-retry-from-reconcile-tasks.md:4 shows status: archived. `| N/A`| PASS `|
`| AC2: #985 is archived `| kanban/tasks/985-wire-real-retry-executor-into-hookreactionrouter.md:4 shows status: archived, but the task body archives it via SPLIT into #991, #992, and #993 rather than by implementation completion.`| N/A `| PASS`|
`| AC3: Together they fulfill the original retry-delegation mandate`| kanban/tasks/991-expose-reaction-executors-dict-from-build-hooks.md:4 is in-progress, kanban/tasks/992-implement-make-retry-executor-and-wire-into-run.md:4 is ideation, and kanban/tasks/993-emit-outcome-budget-exceeded-from-reconcile-tasks.md:4 is todo. src/owlbear/daemon.py:613 still emits outcome failure, and workspace search found no make_retry_executor in src. `| tests/test_daemon_coverage_gaps.py::TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_emits_hook_with_budget_exceeded_outcome; tests/test_daemon_coverage_gaps.py::TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_not_failure; tests/test_daemon_coverage_gaps.py::TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_distinct_from_plain_failure`| FAIL `|
`| AC4: No src/ or tests/ changes from this governance task itself `| kanban/tasks/956-reuse-daemon-retry-state-for-task-scoped.md builder notes state Files changed: none, and the task remains board-only governance work.`| N/A `| PASS`|

### Verdict

- FAIL
- Confidence: .97
- Reason: #956 reached review prematurely. The archived state of #985 is not sufficient because that task was archived via split; its successor work is still open and the remaining retry-delegation behavior is still failing in code and tests.

### Action Taken

- Appended review evidence.
- Returning task #956 to todo for later re-review after the successor chain completes.

[[2026-03-24]] Tue 21:09

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task with no implementation scope)
- Coverage: N/A
- Lint: N/A
- Evidence: Task #984 and task #985 are archived, but split successors are still open. Task #992 is ideation and task #993 is review.
- Fixes applied: None. Task #956 cannot advance until successor chain completion satisfies the retry delegation mandate.

[[2026-03-24]] Tue 22:08

## Test-Writer Notes (retry 4)

- Retry reason: reviewer FAIL was about governance prerequisites (successor tasks not complete), not missing tests.
- Task AC explicitly states: 'No src/ or tests/ changes from this governance task itself.'
- No tests to write or add. Passing through to builder.

[[2026-03-24]] Tue 22:41

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task)
- Coverage: N/A
- Lint: N/A
- Evidence: Child task 984 is archived and child task 985 is archived, but successor task 992 is still todo. Source inspection shows make_retry_executor exists in src/owlbear/daemon.py but run_daemon has no wiring to set hooks reaction retry executor.
- Fixes applied: None. Governance AC line requiring full retry delegation mandate is not yet met.

[[2026-03-24]] Tue 22:45

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about governance state (children #984 and #985 not yet archived), not missing tests.
- No testable implementation in this governance parent - AC explicitly states no src/ or tests/ changes.
- Existing Test-Writer Notes preserved. Builder will address reviewer findings (children must reach archived).

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task with no implementation scope)
- Coverage: N/A
- Lint: N/A
- Evidence: AC1 and AC2 satisfied with child tasks 984 and 985 archived. AC3 not yet satisfied because successor task 992 is currently todo, so the retry delegation mandate is still incomplete.
- Fixes applied: None.

[[2026-03-24]] Tue 23:19

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about governance prerequisites (child tasks not archived), not missing tests.
- Governance parent task. AC explicitly forbids src/ or tests/ changes from this task itself.
- Existing test-writer pass-through notes preserved. Builder must wait for child tasks to complete.

[[2026-03-25]] Wed 00:10

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task)
- Coverage: N/A
- Lint: N/A
- Evidence: Child task 984 is archived and child task 985 is archived, but successor task 992 remains todo so the retry delegation mandate is not fully complete yet.
- Fixes applied: None. No src or tests changes are allowed for this governance parent.

[[2026-03-25]] Wed 01:12

## Test-Writer Notes (retry 6)

[[2026-03-25]] Wed 01:12

## Test-Writer Notes (retry 6)

- Retry reason: reviewer FAIL was about governance prerequisites (successor task 992 still todo), not missing tests.
- Governance parent task. AC explicitly states: No src/ or tests/ changes from this governance task itself.
- No tests to write or modify. Passing through to builder.

[[2026-03-25]] Wed 01:53

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task)
- Coverage: N/A
- Lint: N/A
- Evidence: Task #984 is archived and task #985 is archived, but successor task #992 remains todo. Source scan confirms make_retry_executor exists while run_daemon does not yet reference reaction_executors for retry wiring.
- Fixes applied: None. Parent AC for mandate completion is still blocked by successor completion.

[[2026-03-25]] Wed 02:13

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about child tasks (#984, #985) not yet archived, not about missing tests.
- This is a governance parent with AC explicitly stating: no src/ or tests/ changes from this governance task itself.
- Existing non-impl pass-through preserved. Builder will monitor child task completion.

[[2026-03-25]] Wed 02:35

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task; non-implementation)
- Coverage: N/A
- Lint: N/A
- Evidence: Task #984 archived, #985 archived, #991 archived, #993 archived, and #992 remains todo.
- Fixes applied: None. Parent AC3 remains unmet until #992 is archived.

[[2026-03-25]] Wed 02:40

## Builder Notes

- Files changed: none
- Tests: N/A (governance parent task; non-implementation)
- Coverage: N/A
- Lint: N/A
- Evidence: Task #984 archived, task #985 archived, task #991 archived, task #993 archived, and task #992 remains todo.
- Fixes applied: None. Parent AC3 remains unmet until task #992 is archived.

[[2026-03-25]] Wed 02:51

## Test-Writer Notes (retry)

- Retry reason: latest reviewer FAIL was about governance prerequisites (incomplete child tasks), not missing tests.
- Governance parent task. AC explicitly states: 'No src/ or tests/ changes from this governance task itself.'
- Current child state: #984 archived, #985 archived, #991 archived, #993 archived, #992 in-progress (builder working).
- Passing through unchanged. Builder will address once #992 reaches archived.

[[2026-03-25]] Wed 03:47

## Builder Notes

- Files changed: none.
- Tests: N/A (governance parent task; non-implementation).
- Coverage: N/A.
- Lint: N/A.
- Evidence: AC1 and AC2 are satisfied (#984 archived, #985 archived), but successor task #992 is currently docs (not archived), so AC3 (full retry-delegation mandate completion) is not yet satisfied.
- Fixes applied: None. No src/ or tests/ edits are allowed for this governance parent.

[[2026-03-25]] Wed 05:25

## Test-Writer Notes (retry-2)

- Retry reason: reviewer FAIL was again about governance prerequisites (#984 and #985 not archived), not missing tests.
- This is a governance-only parent task. AC explicitly states: 'No src/ or tests/ changes from this governance task itself.'
- No tests to write. Passing through to builder.

[[2026-03-25]] Wed 06:57

## Builder Notes

- Files changed: none.
- Tests: N/A (governance parent task; non-implementation).
- Coverage: N/A.
- Lint: N/A.
- Evidence: Tasks #984, #985, #991, #992, and #993 are archived, satisfying the governance prerequisite chain for mandate completion.
- Fixes applied: None. Parent task remains board-governance only with no src or tests edits.

[[2026-03-25]] Wed 07:22

## Review Evidence

## Review: #956 - Reuse daemon retry state for task-scoped HookReaction retries

### Test Results

- pytest: 59 passed, 0 failed.
- Evidence: focused slice passed across tests/test_schedule_task_retry.py, tests/test_retry_executor.py, tests/test_992_run_daemon_retry_wiring.py, TestFromAC_ReconcileBudgetExceededOutcome in tests/test_daemon_coverage_gaps.py, TestFromAC_991_BuildHooksReactionExecutors in tests/test_bootstrap.py, and TestFromAC_991_HookRegistryReactionExecutors in tests/test_hooks.py.

### Lint Results

- ruff: All checks passed on src/owlbear/daemon.py, src/owlbear/bootstrap/hooks.py, src/owlbear/core/hooks.py, and the focused tests.

### Coverage

- N/A for governance parent task #956. The parent owns no source or test files.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- N/A for #956 itself. Governance parent task with no task-owned TestFromAC classes.

#### Security Review

- No security issues found in the reviewed source surface. Reviewed daemon retry scheduling, hook executor wiring, and task completion outcome emission.

#### Test Integrity

- N/A for #956 itself. No parent-owned TestFromAC classes were modified.

#### Test Quality

- Assertion specificity: ADEQUATE. Focused tests assert concrete RetryEntry state, emitted outcomes, and wiring presence.
- Negative and error paths: STRONG. BudgetExceededError, missing task_id, exhaustion, duplicate scheduling, and no-reaction defaults are covered.
- Mutation reasoning: ADEQUATE. Removing schedule_task_retry delegation, removing reaction_executors exposure, removing run_daemon wiring, or regressing budget_exceeded outcome would fail the focused slice.
- Test independence: STRONG. Tests use isolated OrchestratorState, AsyncMock kanban, and local HookRegistry instances.
- Descriptive names: STRONG. Test names describe the scenario and expected result.

#### Data Safety

- No data safety issues found. The reviewed path keeps retry state in OrchestratorState.retries and blocks exhausted or budget-exceeded tasks instead of leaving stale runnable state.

#### Implementation-Aware Test Gaps

- No significant untested paths in the governance mandate surface. Code inspection confirms schedule_task_retry exists at src/owlbear/daemon.py:502, make_retry_executor at src/owlbear/daemon.py:572, budget_exceeded emission at src/owlbear/daemon.py:667, run_daemon retry wiring at src/owlbear/daemon.py:1142, reaction_executors exposure at src/owlbear/bootstrap/hooks.py:73, and HookRegistry.reaction_executors default at src/owlbear/core/hooks.py:191.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

- AC1: #984 archived. Evidence: kanban/tasks/984-extract-schedule-task-retry-from-reconcile-tasks.md status is archived. Mapped test: N/A. Status: PASS.
- AC2: #985 archived. Evidence: kanban/tasks/985-wire-real-retry-executor-into-hookreactionrouter.md status is archived. Mapped test: N/A. Status: PASS.
- AC3: original mandate fulfilled. Evidence: current source wires task completion failures into the extracted scheduler and shared retry state, while BudgetExceededError emits budget_exceeded instead of failure. Focused pytest slice passed 59 tests covering scheduler extraction, reconcile delegation, retry executor real-payload scheduling, duplicate-schedule idempotency, reaction_executors exposure, run_daemon wiring, and budget_exceeded outcome emission. Mapped tests: TestFromAC_ReconcileCallsScheduleTaskRetry::test_reconcile_passes_custom_retry_config, TestFromAC_RetryExecutorRealPayload::test_retry_executor_integration_real_daemon_payload, TestFromAC_RetryExecutorIntegration::test_retry_executor_daemon_order_does_not_double_schedule, TestFromAC_RunDaemonRetryWiring::test_wired_executor_schedules_retry_on_failure, TestFromAC_ReconcileBudgetExceededOutcome::test_budget_exceeded_outcome_distinct_from_plain_failure, TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_same_object_passed_to_router. Status: PASS.
- AC4: no src or tests changes from this governance parent itself. Evidence: recent implementation history shows source and test commits tagged to child tasks #984, #991, #992, and #993, while #956 remains board-governance only and the latest builder note reports no parent-owned src or tests files. Mapped test: N/A. Status: PASS.

### Verdict: PASS

- Confidence: .95

### Action Taken

- Appended review evidence.
- Prepared to move task #956 to docs and release the claim.
