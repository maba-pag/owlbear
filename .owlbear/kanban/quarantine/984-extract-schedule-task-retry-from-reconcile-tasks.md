---
id: 984
title: Extract schedule_task_retry from reconcile_tasks
status: archived
priority: needed
created: 2026-03-24T03:57:43.6034676+01:00
updated: 2026-03-24T17:00:49.1136369+01:00
started: 2026-03-24T17:00:43.7330288+01:00
completed: 2026-03-24T17:00:43.7330288+01:00
tags:
    - daemon
    - hooks
    - scope:core
    - type:build
parent: 956
depends_on:
    - 955
class: standard
---

Extract `schedule_task_retry` from `reconcile_tasks()` as a standalone idempotent async function. Refactor `reconcile_tasks` to call it.

See docs/research/hook-reaction-retry-delegation.md section 4 steps 1-2.

## Acceptance Criteria

- [ ] AC1: `async def schedule_task_retry(*, state: OrchestratorState, kanban: KanbanToolset, task_id: str, error: Exception, max_attempts: int, backoff_base: float, backoff_max: float) -> None` exists as a module-level function in `src/owlbear/daemon.py`.
- [ ] AC2: `BudgetExceededError` branch â€” when `isinstance(error, BudgetExceededError)` is true, calls `kanban.kanban_edit(task_id, block=...)` and `state.claimed.discard(task_id)`. No `RetryEntry` is created.
- [ ] AC3: Exhaustion branch â€” when `next_attempt > max_attempts`, calls `kanban.kanban_edit(task_id, block=...)` with exhaustion reason, pops `state.retries[task_id]`, discards from `state.claimed`.
- [ ] AC4: Retry branch â€” when retries remain, computes delay via `_compute_retry_delay(attempt=next_attempt, base=backoff_base, maximum=backoff_max)` and writes `RetryEntry` to `state.retries[task_id]` with correct `attempt`, `next_due`, and `last_error`.
- [ ] AC5: Idempotent â€” if `state.retries[task_id].attempt >= computed_next_attempt`, the function returns without side effects (no kanban call, no state mutation).
- [ ] AC6: `reconcile_tasks()` calls `schedule_task_retry()` instead of inline retry logic (replaces lines ~560-596 with a single await call). No behavioral change in `reconcile_tasks`.
- [ ] AC7: All 17+ existing `reconcile_tasks` test classes pass unchanged (regression gate: `tests/test_poll_dispatch.py`, `tests/test_daemon_coverage_gaps.py`, `tests/test_budget_threshold.py`, `tests/test_lint_gate.py`).
- [ ] AC8: All RED-phase tests from #990 pass (GREEN phase).
- [ ] AC9: `ruff check` clean on changed files.

Depends on: #955 (archived), #990 (TDD RED tests).

## Research

See research section from prior revision — full checklist validated in researcher pass. Key points:

- Retry logic at daemon.py:560-596 is ~35 lines with clear inputs/outputs
- 17+ test classes across 4 files cover existing retry paths (regression base)
- Idempotency guard: check state.retries[tid] for same-or-higher attempt before writing
- Budget-bypass: isinstance(exc, BudgetExceededError) check
- See docs/research/hook-reaction-retry-delegation.md section 4 steps 1-2

[[2026-03-24]] Tue 04:47

## Research

See docs/research/hook-reaction-retry-delegation.md section 4 steps 1-2.
Retry logic at daemon.py:560-596 (~35 lines), 17+ test classes across 4 files for regression base.
Idempotency guard: check state.retries[tid] for same-or-higher attempt.
Budget-bypass: isinstance(exc, BudgetExceededError) check.

[[2026-03-24]] Tue 04:48

## Architecture Review

**Verdict:** APPROVED (after refinement and TDD split)

### AC Assessment

| AC Line | Assessment | Action |

|---------|------------|--------|

| (original 1) schedule_task_retry exists | Clear, verifiable | Refined: added full type signature |

| (original 2) reconcile_tasks calls it | Vague on extraction boundary | Refined: specifies line range replaced |

| (original 3) idempotent | Clear, testable | Kept, renumbered AC5 |

| (original 4) existing tests pass | Clear regression gate | Kept, renumbered AC7 |

| (original 5) new unit tests | TDD violation: bundled tests in impl task | Split: created #990 as TDD RED predecessor |

### Architecture Notes

- Function stays in daemon.py (bootstrap/assembly layer). No new module boundaries. No layering violation.

- OrchestratorState.retries remains single source of truth for retry state (src/owlbear/daemon.py:118).

- Idempotency guard enables safe reuse by hook reaction executor (#985). Dedup via same-or-higher attempt.

- BudgetExceededError import stays as lazy import inside the function (matching existing pattern).

- _compute_retry_delay() reused as-is (pure function, no changes needed).

- state.claimed.discard() is included in extracted function for budget/exhaustion paths only.

- Single domain: bootstrap (daemon.py). No cross-domain violation.

[[2026-03-24]] Tue 09:27

## Test-Writer Notes

- Test file: tests/test_schedule_task_retry.py
- Classes added for #984:
  - TestFromAC_ScheduleTaskRetry_Signature (AC1 - signature/importability, 4 tests)
  - TestFromAC_ReconcileCallsScheduleTaskRetry (AC6 - reconcile delegates, 5 tests)
- Pre-existing classes from #990 (AC2/AC3/AC4/AC5): 21 tests across 5 classes
- Tests per category: happy 16, edge 5, error 7, boundary 2
- Total: 30 tests, all FAIL (ImportError / AttributeError) checked
- ruff: clean
- AC coverage: AC1-AC6 all have 2+ tests

[[2026-03-24]] Tue 09:27

## Test-Writer Notes

- Test file: tests/test_schedule_task_retry.py
- Classes added for #984:
  - TestFromAC_ScheduleTaskRetry_Signature (AC1 - signature/importability, 4 tests)
  - TestFromAC_ReconcileCallsScheduleTaskRetry (AC6 - reconcile delegates, 5 tests)
- Pre-existing classes from #990 (AC2/AC3/AC4/AC5): 21 tests across 5 classes
- Tests per category: happy 16, edge 5, error 7, boundary 2
- Total: 30 tests, all FAIL (ImportError / AttributeError) checked
- ruff: clean
- AC coverage: AC1-AC6 all have 2+ tests

[[2026-03-24]] Tue 10:09

## Builder Notes

- Files changed: src/owlbear/daemon.py
- Tests: 30 passed in tests/test_schedule_task_retry.py. Task related regression: 223 passed and 2 deselected in daemon gate files.
- Coverage: src/owlbear/daemon.py 96 percent from daemon focused run with 326 passed and 2 deselected.
- Lint: ruff check passed for src/owlbear/daemon.py and tests/test_schedule_task_retry.py.
- Fixes applied: Extracted schedule_task_retry and delegated reconcile_tasks failure retry handling.

[[2026-03-24]] Tue 11:12

## Review Evidence

## Review: #984 - Extract schedule_task_retry from reconcile_tasks

### Test Results

- Task tests: `uv run pytest tests/test_schedule_task_retry.py -q --tb=short` -> 30 passed, 2 warnings.
- AC7 file-level regression run: `uv run pytest tests/test_poll_dispatch.py tests/test_daemon_coverage_gaps.py tests/test_budget_threshold.py tests/test_lint_gate.py -q --tb=short` -> 223 passed, 2 failed in unrelated `TestFromAC_809_RunBuilderContextFallback` in `tests/test_daemon_coverage_gaps.py:2809` and `tests/test_daemon_coverage_gaps.py:2835`.
- Task-scoped regression rerun: `uv run pytest tests/test_poll_dispatch.py tests/test_daemon_coverage_gaps.py tests/test_budget_threshold.py tests/test_lint_gate.py -q --tb=short -k "not RunBuilderContextFallback"` -> 223 passed, 2 deselected, 4 warnings.
- Bug reproduction: seeded `state.retries['budget-task']` then called `schedule_task_retry(..., error=BudgetExceededError(...))` via `uv run python -c ...` -> output was `retry_present True`, `claimed_present False`, `kanban_edit_calls 1`.

### Lint Results

- `uv run ruff check src/owlbear/daemon.py tests/test_schedule_task_retry.py` -> All checks passed.

### Coverage

- Partial 5-file scope: `src/owlbear/daemon.py` 72% (not enough to represent the daemon-focused surface).
- Broader daemon scope: `uv run pytest tests/test_daemon.py tests/test_schedule_task_retry.py tests/test_poll_dispatch.py tests/test_daemon_coverage_gaps.py tests/test_budget_threshold.py tests/test_lint_gate.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -k "not RunBuilderContextFallback"` -> `src/owlbear/daemon.py` 96%, 326 passed, 2 deselected.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| AC1: module-level async function with required keyword-only signature | `tests/test_schedule_task_retry.py:648-690` (`TestFromAC_ScheduleTaskRetry_Signature`) | Yes | COVERED |
| AC2: BudgetExceededError blocks, discards claim, leaves no retry scheduled | `tests/test_schedule_task_retry.py:348-444`; `tests/test_budget_threshold.py:322-374` | No. All tests start from fresh retry state and miss the case where a pre-existing retry entry survives the budget block. | LAX |
| AC3: exhaustion blocks, pops retries, discards claim | `tests/test_schedule_task_retry.py:237-344`; `tests/test_daemon_coverage_gaps.py:74-181`; `tests/test_poll_dispatch.py:2075-2133` | Yes | COVERED |
| AC4: retry path writes RetryEntry with attempt/next_due/last_error | `tests/test_schedule_task_retry.py:46-234`; `tests/test_poll_dispatch.py:1893-2069` | Yes | COVERED |
| AC5: idempotent no-op when same-or-higher attempt already exists | `tests/test_schedule_task_retry.py:452-580` | Yes for concurrent same-attempt writes | COVERED |
| AC6: reconcile_tasks delegates to schedule_task_retry | `tests/test_schedule_task_retry.py:698-850` | Yes for delegation; source also confirms the inline block was replaced by a single await call. | COVERED |
| AC7: existing reconcile_tasks classes still pass | Named regression files above, task-scoped rerun excluding unrelated `RunBuilderContextFallback` | Yes | COVERED |
| AC8: RED tests from #990 pass | `tests/test_schedule_task_retry.py` full file run | Yes | COVERED |
| AC9: Ruff clean on changed files | Ruff run above | Yes | COVERED |

#### Security Review

- No hardcoded secrets, injection, traversal, unsafe deserialization, or dependency changes found in the builder diff. Commit `5bf5fd0` touched only `src/owlbear/daemon.py`.

#### Test Integrity

| Original Test | Change Made | Assessment |
| --- | --- | --- |
| All `TestFromAC_*` coverage in `tests/test_schedule_task_retry.py` | `git diff --unified=3 d6f6eaa..5bf5fd0 -- tests/test_schedule_task_retry.py` returned no diff; builder commit `5bf5fd0` touched only `src/owlbear/daemon.py` | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | ADEQUATE | Tests assert concrete `RetryEntry` fields, `kanban_edit` calls, and forwarded kwargs. |
| Negative / error paths | STRONG | Budget, exhaustion, kanban failure, and reconcile failure paths are all exercised. |
| Mutation reasoning | WEAK | No test seeds an existing retry entry before the BudgetExceededError branch. The current implementation leaves stale retry state behind, and the suite still passes. |
| Test independence | STRONG | Each test creates fresh `OrchestratorState`, mocks, and task IDs. |
| Descriptive names | STRONG | Names describe the scenario and expected outcome precisely. |

#### Data Safety

- FAIL: `src/owlbear/daemon.py:523-530` blocks budget-exceeded tasks and drops the claim, but it never clears `state.retries[task_id]` before returning.
- `src/owlbear/daemon.py:804-810` later redispatches any due entry that remains in `state.retries` without checking blocked state.
- The reproduction command confirmed the stale retry remains after the budget block (`retry_present True`). That means a permanently blocked task can be retried later.

#### Implementation-Aware Test Gaps

- The extracted standalone helper now has a state combination the old inline path did not expose: BudgetExceededError plus a pre-existing retry entry.
- `tests/test_schedule_task_retry.py:398-416` only proves the budget branch does not create a retry from an empty state; it does not prove the branch clears an existing retry.
- Because `poll_tick` re-dispatches from `state.retries`, the missing test allowed a real behavior regression through review.

### Pass 2 - INFORMATIONAL

- No additional informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| AC1 | `src/owlbear/daemon.py:506-514` defines `schedule_task_retry` with the required signature. | `tests/test_schedule_task_retry.py:648-690` | PASS |
| AC2 | `src/owlbear/daemon.py:523-530` blocks and discards claim but does not clear an existing retry entry; reproduction left `retry_present True`. | `tests/test_schedule_task_retry.py:348-444` and `tests/test_budget_threshold.py:322-374` miss this state. | FAIL |
| AC3 | `src/owlbear/daemon.py:541-549` blocks exhausted retries, pops `state.retries`, and discards claim. | `tests/test_schedule_task_retry.py:237-344`; `tests/test_daemon_coverage_gaps.py:74-181`; `tests/test_poll_dispatch.py:2075-2133` | PASS |
| AC4 | `src/owlbear/daemon.py:551-560` computes delay and writes `RetryEntry(attempt, next_due, last_error)`. | `tests/test_schedule_task_retry.py:46-234`; `tests/test_poll_dispatch.py:1893-2069` | PASS |
| AC5 | `src/owlbear/daemon.py:532-539` implements the idempotency guard after a yield point. | `tests/test_schedule_task_retry.py:452-580` | PASS |
| AC6 | `src/owlbear/daemon.py:615-621` replaces inline retry handling with a single `await schedule_task_retry(...)`. | `tests/test_schedule_task_retry.py:698-850` | PASS |
| AC7 | Relevant reconcile regression surface in the named files passed in the task-scoped rerun (223 passed, 2 deselected). | Regression commands above | PASS |
| AC8 | RED-phase suite passed. | `tests/test_schedule_task_retry.py` -> 30 passed | PASS |
| AC9 | Ruff clean on reviewed files. | Ruff command above | PASS |

### Verdict

- FAIL
- Confidence: .96
- Reason: the extracted standalone helper leaves stale retry state behind on the BudgetExceededError path when a retry entry already exists, so a permanently blocked task can later be re-dispatched. The current tests missed that path.

### Action Taken

- `kanban\kanban-md.exe edit 984 -a <review evidence> -t --claim reviewer`

[[2026-03-24]] Tue 13:04

## Test-Writer Notes (retry)\n- Retry: AC2 gap - BudgetExceededError path does not clear pre-existing retry entry.\n- Added: test_budget_exceeded_clears_existing_retry_entry (FAIL confirmed: AssertionError).\n- Preserved: 30 existing tests (PASS). ruff: clean

[[2026-03-24]] Tue 13:04

## Test-Writer Notes (retry) - Added test_budget_exceeded_clears_existing_retry_entry. Retry reason: AC2 budget path leaves stale retry entry. New test FAILs (AssertionError). 30 old tests preserved (PASS). ruff clean

[[2026-03-24]] Tue 13:27

## Builder Notes

- Files changed: src/owlbear/daemon.py
- Tests: tests/test_schedule_task_retry.py -> 31 passed; AC7 regression files -> 223 passed, 2 failed (known unrelated TestFromAC_809_RunBuilderContextFallback); daemon-focused coverage suite -> 327 passed, 2 deselected
- Coverage: src/owlbear/daemon.py 96% (bare --cov run)
- Lint: ruff clean on src/owlbear/daemon.py and tests/test_schedule_task_retry.py
- Evidence: RED before fix had 1 failing test (test_budget_exceeded_clears_existing_retry_entry); GREEN after fix is 31 passed in tests/test_schedule_task_retry.py
- Fixes applied: schedule_task_retry BudgetExceededError branch now clears stale retry entry via state.retries.pop(task_id, None)

[[2026-03-24]] Tue 14:07

## Review Evidence

## Review: #984 - Extract schedule_task_retry from reconcile_tasks (rerun)

### Findings

- FAIL: AC1's exact typed signature is only partially tested. The signature class at tests/test_schedule_task_retry.py:678 checks importability, coroutine status, parameter presence, and keyword-only shape, but it never asserts the required annotations for state, kanban, task_id, error, max_attempts, backoff_base, backoff_max, or the None return annotation. The implementation at src/owlbear/daemon.py:506 currently satisfies the contract, but removing those annotations would still leave the task suite green. No compensating builder-discovered test exists.

### Test Results

- Task suite: 35 passed, 2 warnings.
- Regression slice: 223 passed, 2 deselected, 4 warnings.
- Daemon-focused coverage suite: 331 passed, 2 deselected, 4 warnings.

### Lint Results

- Ruff: all checks passed on src/owlbear/daemon.py and tests/test_schedule_task_retry.py.

### Coverage

- src/owlbear/daemon.py: 96 percent in the daemon-focused bare coverage run.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| AC1 exact typed module-level async signature | tests/test_schedule_task_retry.py:678-726 | No. Annotation contract is untested. | LAX |
| AC2 budget block clears retry and discards claim | tests/test_schedule_task_retry.py:348-471 and 1007-1028 | Yes | COVERED |
| AC3 exhaustion blocks and cleans state | tests/test_schedule_task_retry.py:241-344 | Yes | COVERED |
| AC4 retry branch writes correct RetryEntry fields | tests/test_schedule_task_retry.py:46-229 | Yes | COVERED |
| AC5 idempotency guard prevents duplicate writes | tests/test_schedule_task_retry.py:479-597 and 890-964 | Yes | COVERED |
| AC6 reconcile delegates to schedule_task_retry | tests/test_schedule_task_retry.py:728-887 and src/owlbear/daemon.py:616 | Yes | COVERED |
| AC7 regression surface still passes | named regression slice | Yes | COVERED |
| AC8 RED-phase tests now pass | tests/test_schedule_task_retry.py full run | Yes | COVERED |
| AC9 lint clean on changed files | ruff run | Yes | COVERED |

#### Security Review

- No security issues found. Builder commit d8c19db added one line at src/owlbear/daemon.py:529 and no new dependency or input surface.

#### Test Integrity

| Original Test | Change Made | Assessment |
| --- | --- | --- |
| All TestFromAC tests in tests/test_schedule_task_retry.py | git diff from 01c7e83 to d8c19db for that file was empty | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | ADEQUATE | Runtime branches are asserted concretely, but AC1 only checks signature shape, not the typed contract. |
| Negative and error paths | STRONG | Budget, exhaustion, kanban failure, idempotency, and reconcile delegation paths are exercised. |
| Mutation reasoning | WEAK | Removing parameter annotations or the None return annotation from src/owlbear/daemon.py:506 would still leave all 35 task tests green. |
| Test independence | STRONG | Fresh state and mocks are used across the suite. |
| Descriptive names | STRONG | Test names map directly to the behavior under review. |

#### Data Safety

- No remaining data-safety issue found after the stale-retry fix at src/owlbear/daemon.py:529.

#### Implementation-Aware Test Gaps

- The exact typed signature is part of the public contract for this extraction task and remains unpinned by tests. A future refactor could strip those annotations without tripping the suite.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| AC1 | src/owlbear/daemon.py:506-514 has the required typed signature, but tests/test_schedule_task_retry.py:678-726 only partially verify it | TestFromAC_ScheduleTaskRetry_Signature | FAIL |
| AC2 | src/owlbear/daemon.py:523-530 blocks budget errors, pops retries, and discards claim | budget class | PASS |
| AC3 | src/owlbear/daemon.py:542-549 blocks exhaustion and cleans state | exhaustion class | PASS |
| AC4 | src/owlbear/daemon.py:552-561 computes delay and writes RetryEntry | schedule class | PASS |
| AC5 | src/owlbear/daemon.py:537-539 guards duplicate writes | idempotency classes | PASS |
| AC6 | src/owlbear/daemon.py:616-621 delegates from reconcile_tasks | reconcile delegation class | PASS |
| AC7 | regression slice passed | regression suite | PASS |
| AC8 | task suite passed | tests/test_schedule_task_retry.py | PASS |
| AC9 | ruff clean | lint run | PASS |

### Verdict

- FAIL
- Confidence: .91
- Reason: implementation is currently correct, but the reviewer gate cannot PASS because AC1's exact typed signature is not enforced by the tests.

[[2026-03-24]] Tue 16:00

## Builder Notes

- Files changed: none
- Tests: 38 passed in tests/test_schedule_task_retry.py; 223 passed with 4 deselected in the AC7 regression slice; 334 passed with 4 deselected in the daemon-focused coverage slice.
- Coverage: src/owlbear/daemon.py 96 percent in the daemon-focused coverage run.
- Lint: ruff clean on src/owlbear/daemon.py and tests/test_schedule_task_retry.py.
- Evidence: The task suite was green on arrival before implementation work, and all #984 verification reruns stayed green.
- Fixes applied: None (no-code-change GREEN confirmation).

[[2026-03-24]] Tue 16:32

## Review Evidence

### Findings

- No blocking findings.

### Test Results

- Task suite on tests/test_schedule_task_retry.py: 38 passed, 2 warnings.
- AC1 signature class on tests/test_schedule_task_retry.py: 7 passed, 2 warnings.
- Full four-file regression slice: 223 passed, 4 failed, 4 warnings. The four failures are in tests/test_daemon_coverage_gaps.py lines 2772 through 2922 and exercise_run_builder_with_context, not reconcile_tasks or schedule_task_retry.
- Task-relevant AC7 rerun excluding those two unrelated classes: 223 passed, 4 deselected, 4 warnings.

### Lint Results

- Ruff passed on src/owlbear/daemon.py and tests/test_schedule_task_retry.py.

### Coverage

- Daemon-focused coverage slice: 334 passed, 4 deselected, 4 warnings.
- src/owlbear/daemon.py measured 96 percent coverage in that slice.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 is covered by TestFromAC_ScheduleTaskRetry_Signature at tests/test_schedule_task_retry.py lines 678 through 785. The class now pins exact annotations for state, kanban, task_id, error, max_attempts, backoff_base, backoff_max, and the None return annotation. The direct class run passed 7 tests.
- AC2 is covered by TestFromAC_ScheduleTaskRetry_BudgetExceeded at tests/test_schedule_task_retry.py lines 348 through 471 plus TestFromAC_ReconcileBudgetExceeded at tests/test_budget_threshold.py lines 323 through 369. The stale-retry cleanup path is explicitly covered by test_budget_exceeded_clears_existing_retry_entry.
- AC3 is covered by the exhaustion class at tests/test_schedule_task_retry.py lines 237 through 344 plus the existing reconcile regression surface. Current source clears retries and claims at src/owlbear/daemon.py lines 542 through 549.
- AC4 is covered by the retry scheduling class at tests/test_schedule_task_retry.py lines 46 through 234. Current source computes delay and writes RetryEntry at src/owlbear/daemon.py lines 551 through 561.
- AC5 is covered by the original idempotency class plus the higher-attempt class at tests/test_schedule_task_retry.py lines 449 through 597 and 972 through 1033. The guard at src/owlbear/daemon.py lines 536 through 539 is exercised for both equal and greater attempts.
- AC6 is covered by TestFromAC_ReconcileCallsScheduleTaskRetry at tests/test_schedule_task_retry.py lines 792 through 964. Current source delegates with a single await at src/owlbear/daemon.py lines 616 through 621.
- AC7 is covered by the task-relevant four-file rerun with the unrelated _run_builder_with_context classes deselected.
- AC8 is covered by the task suite pass.
- AC9 is covered by the Ruff pass.

#### Security Review

- No security issues found in src/owlbear/daemon.py lines 506 through 621. No new dependency or input surface was introduced by the extraction.

#### Test Integrity

- git log on tests/test_schedule_task_retry.py returned b9506af as the latest commit touching the file.
- git diff from b9506af to current HEAD on tests/test_schedule_task_retry.py was empty, so the latest TestFromAC coverage was preserved exactly.

#### Test Quality

- Assertion specificity: STRONG. The suite checks exact annotations, exact forwarded kwargs, exact retry state, and exact kanban behavior.
- Negative and error paths: STRONG. Budget-exceeded, exhaustion, kanban-edit failure logging, idempotency, and reconcile success and failure delegation are all covered.
- Mutation reasoning: STRONG. Removing the budget retry cleanup, stripping annotations, removing logger.warning, or weakening the higher-attempt guard would fail the current suite.
- Test independence: STRONG. Tests build fresh state and mocks, and both the focused AC1 class and the full task file pass cleanly.
- Descriptive names: STRONG. Names map directly to the acceptance criteria and to the prior reviewer findings.

#### Data Safety

- No data safety issues found. Budget blocks now clear stale retry state before returning, which prevents poll_tick from redispatching blocked tasks.

#### Implementation-Aware Test Gaps

- No significant untested path remains in the extracted helper or its reconcile integration. The meaningful branches in schedule_task_retry are all covered, including the two gaps that caused earlier retry cycles.

### Pass 2 - INFORMATIONAL

- The unfiltered four-file regression slice still has four unrelated failures in tests/test_daemon_coverage_gaps.py for_run_builder_with_context. They do not exercise schedule_task_retry or reconcile_tasks, so they do not block task 984.

### AC Compliance

- AC1 PASS: src/owlbear/daemon.py lines 506 through 514 define the required typed signature, and the signature class lines 678 through 785 pin the exact annotation contract.
- AC2 PASS: src/owlbear/daemon.py lines 523 through 530 block budget errors, clear retries, and discard claims. The stale-retry regression is covered at tests/test_schedule_task_retry.py lines 449 through 471 and the reconcile path at tests/test_budget_threshold.py lines 323 through 369.
- AC3 PASS: src/owlbear/daemon.py lines 542 through 549 block exhausted retries and clean state. Exhaustion tests remain green.
- AC4 PASS: src/owlbear/daemon.py lines 551 through 561 compute delay and store RetryEntry. Scheduling tests remain green.
- AC5 PASS: src/owlbear/daemon.py lines 536 through 539 implement the no-op guard, and both same-attempt and higher-attempt concurrency tests pass.
- AC6 PASS: src/owlbear/daemon.py lines 616 through 621 delegate retry handling from reconcile_tasks, and the delegation class remains green.
- AC7 PASS: the task-relevant regression slice passed 223 tests with 4 unrelated classes deselected.
- AC8 PASS: tests/test_schedule_task_retry.py passed 38 tests.
- AC9 PASS: Ruff passed.

### Verdict

- PASS
- Confidence: .94

-t

[[2026-03-24]] Tue 16:45

## Docs Gate

Checklist:

1. copilot-instructions.md: N/A. Refactoring task, behavior unchanged. Retry executor already referenced via #956. schedule_task_retry is an internal daemon helper.
2. Docstrings: Pass. schedule_task_retry at src/owlbear/daemon.py:506 has a docstring covering purpose and idempotency. reconcile_tasks docstring still accurate.
3. docs/sources/overview.md: N/A. No new external patterns. Attribution already present under Hook Reaction Retry Delegation (Task 956) section.
4. README.md: N/A. No CLI changes.
5. Research doc: Pass. docs/research/hook-reaction-retry-delegation.md exists and is linked from the task body.
Scratch files cleaned: 984-ac.tmp, 984-builder-notes.tmp, 984-builder.tmp, 984-check.txt, 984-notes.tmp, 984-pytest.tmp, 984-ruff.txt, 984-ruff2.txt, 984-test-writer-retry.tmp, 984-tw-check.txt, 984-tw-check2.tmp.
Files updated: None.

[[2026-03-24]] Tue 17:00

## Audit

### AC Verification

AC1 function signature: schedule_task_retry at src/owlbear/daemon.py:506-514 with required kw-only params. PASS.
AC2 BudgetExceededError branch: Lines 522-531 block, pop retries, discard claim. Fix commit d8c19db added state.retries.pop at line 530. PASS.
AC3 exhaustion branch: Lines 541-549 block, pop retries, discard claim. PASS.
AC4 retry branch: Lines 551-560 compute delay and write RetryEntry. PASS.
AC5 idempotent guard: Lines 536-539 check current.attempt >= next_attempt. PASS.
AC6 reconcile delegates: Lines 615-623 single await schedule_task_retry call. PASS.
AC7 regression gate: 333 passed, 1 pre-existing failure (test_wip_loaded_into_retry_prompt broken async config since 9edecc9), 4 deselected. PASS.
AC8 #990 RED tests pass: 38 passed in test_schedule_task_retry.py. PASS.
AC9 ruff clean: All checks passed on daemon.py and test_schedule_task_retry.py. PASS.

### Test Results

Daemon regression: 333 passed, 1 pre-existing failure, 4 deselected.
Task tests: 38 passed in tests/test_schedule_task_retry.py.
ruff: All checks passed.

### Reviewer FAIL Resolution

Reviewer found AC2 stale-retry data safety bug. Builder fix commit d8c19db added state.retries.pop(task_id, None) to BudgetExceededError branch. Verified in current code at line 530.

### Architect Quality

AC specificity: 8 of 9 AC items were concrete and verifiable. AC2 missed the stale-retry edge case.
Edge case coverage: one notable gap caught in review and fixed by builder.
Design direction: architecture notes led builder cleanly.
AC quality score: 4.

### Confidence: .96

### Action: archive
