---
id: 990
title: 'Test: schedule_task_retry standalone (TDD RED)'
status: archived
priority: needed
created: 2026-03-24T04:45:24.3260912+01:00
updated: 2026-03-24T15:52:51.7869407+01:00
started: 2026-03-24T15:52:04.5347666+01:00
completed: 2026-03-24T15:52:04.5347666+01:00
tags:
    - daemon
    - hooks
    - scope:core
    - type:test
    - test
depends_on:
    - 955
class: standard
---

RED-phase tests for the `schedule_task_retry` function extracted from `reconcile_tasks` (#984).

## Acceptance Criteria

- [ ] AC1: New `TestFromAC_ScheduleTaskRetry` test class(es) exist. Test file at test-writer's discretion (`tests/test_poll_dispatch.py` or new file).
- [ ] AC2: Tests cover successful retry scheduling â€” `state.retries[tid]` receives a `RetryEntry` with correct `attempt`, delay computed via `_compute_retry_delay()`, and `last_error` set.
- [ ] AC3: Tests cover exhaustion blocking â€” when attempt exceeds `max_attempts`, `kanban.kanban_edit(tid, block=...)` is called, `state.retries[tid]` is popped, `state.claimed` discard is called.
- [ ] AC4: Tests cover budget-exceeded bypass â€” when `error` is a `BudgetExceededError`, `kanban.kanban_edit(tid, block=...)` is called, `state.claimed` is discarded, no `RetryEntry` is created.
- [ ] AC5: Tests cover idempotency â€” calling twice for same `task_id` at same or lower attempt produces no side effects on the second call (no kanban call, no state mutation).
- [ ] AC6: Tests cover kanban call failure during block â€” `kanban.kanban_edit` raises, exception is logged but not propagated.
- [ ] AC7: All tests fail (RED phase) since `schedule_task_retry` does not yet exist as a standalone function.

[[2026-03-24]] Tue 09:24

## Test-Writer Notes

- Test file: tests/test_schedule_task_retry.py
- Classes: TestFromAC_ScheduleTaskRetry_Schedule, TestFromAC_ScheduleTaskRetry_Exhaustion, TestFromAC_ScheduleTaskRetry_BudgetExceeded, TestFromAC_ScheduleTaskRetry_Idempotency, TestFromAC_ScheduleTaskRetry_KanbanFailure
- Tests per category: happy 8, edge 3, error 7, boundary 3
- Total: 21 tests, all FAIL (ImportError: schedule_task_retry not yet in daemon.py) ✓
- ruff: clean
- AC coverage:
  AC1: TestFromAC_ScheduleTaskRetry_* classes exist in tests/test_schedule_task_retry.py
  AC2: test_first_failure_creates_retry_entry, test_first_failure_attempt_is_one, test_entry_delay_matches_compute_retry_delay, test_entry_last_error_contains_exception_message, test_task_stays_in_claimed_after_scheduling, test_second_failure_increments_attempt, test_second_failure_delay_doubles, test_normal_retry_does_not_call_kanban_edit
  AC3: test_exhaustion_calls_kanban_edit_with_block, test_exhaustion_pops_from_retries, test_exhaustion_discards_from_claimed, test_exhaustion_block_reason_mentions_attempts
  AC4: test_budget_exceeded_calls_kanban_edit, test_budget_exceeded_discards_from_claimed, test_budget_exceeded_no_retry_entry_created, test_budget_exceeded_block_reason_mentions_budget
  AC5: test_idempotent_concurrent_calls_write_retry_once, test_idempotent_concurrent_no_extra_kanban_call, test_idempotent_guard_prevents_lower_attempt_overwrite
  AC6: test_kanban_failure_during_exhaustion_not_propagated, test_kanban_failure_during_budget_block_not_propagated
  AC7: All 21 fail in RED phase ✓

[[2026-03-24]] Tue 11:02

## Builder Notes

- Files changed: none
- Tests: 30 passed in tests/test_schedule_task_retry.py
- Coverage: src/owlbear/daemon.py 28% in scoped --cov run (no implementation changes in this builder pass)
- Lint: ruff clean on src/owlbear/daemon.py and tests/test_schedule_task_retry.py
- Evidence: RED verification expected ImportError but observed 30/30 passing; schedule_task_retry already exists and reconcile_tasks already delegates to it
- Fixes applied: None (task was already GREEN before builder execution)

[[2026-03-24]] Tue 12:59

## Review Evidence\n### Test Results\n- pytest: 30 passed, 2 warnings via uv run pytest tests/test_schedule_task_retry.py -q --tb=short.\n- ruff: clean via uv run ruff check src/owlbear/daemon.py tests/test_schedule_task_retry.py.\n- coverage: src/owlbear/daemon.py reported 28% in the scoped bare --cov run; manual branch review was used for the task-specific function paths.\n\n### Critical Findings\n- AC5 FAIL: daemon.py lines 536-538 guard same or lower attempts, but tests/test_schedule_task_retry.py lines 453, 494, and 528 only prove same-attempt concurrency from empty state. No test proves a stale lower-attempt caller is a no-op against a higher current attempt.\n- AC6 FAIL: daemon.py lines 528 and 546 log kanban block failures, but tests/test_schedule_task_retry.py lines 592 and 617 assert only non-propagation and cleanup. Logging is unverified.\n- AC7 FAIL: tests/test_schedule_task_retry.py line 8 still declares RED-only behavior, yet pytest now reports 30 passed and line 651 imports schedule_task_retry. Git history shows commit 5bf5fd0 extracted schedule_task_retry for task 984 before this review.\n\n### Additional Evidence\n- git diff --unified=0 e152655 HEAD -- tests/test_schedule_task_retry.py shows the original 990 TestFromAC blocks were preserved; later changes only added 984 header/import updates and appended classes.\n- Security and data-safety review of daemon.py lines 506-561, 615-622, and 810 found no separate issues.\n\n### Verdict\n- FAIL: return to todo

-t

[[2026-03-24]] Tue 13:42

## Test-Writer Notes (retry)

- Retry reason: reviewer cited AC5 gap (stale lower-attempt guard) and AC6 gap (logging not asserted).
- Added 4 new tests in 2 new TestFromAC_ classes:
  - TestFromAC_ScheduleTaskRetry_IdempotencyGuardHigherAttempt (2 tests): test_guard_skips_when_current_attempt_exceeds_next_attempt, test_guard_skips_produces_no_kanban_call.
  - TestFromAC_ScheduleTaskRetry_KanbanFailureLogging (2 tests): test_kanban_failure_during_exhaustion_logs_warning, test_kanban_failure_during_budget_block_logs_warning.
- Preserved: 31 existing tests, all PASS.
- AC5 gap closed: concurrent write to attempt=3 while guarded call computed next_attempt=2; guard current.attempt > next_attempt fires, state not overwritten.
- AC6 gap closed: logger.warning assert_called_once() with task_id present in call args for both exhaustion and budget paths.
- AC7 note: schedule_task_retry exists since commit 5bf5fd0 (#984); all 35 tests pass. RED-only header is a known artifact.
- ruff: clean.
- Total: 35 tests, all PASS.

[[2026-03-24]] Tue 13:42

## Test-Writer Notes (retry)

- Retry reason: reviewer cited AC5 gap (stale lower-attempt guard) and AC6 gap (logging not asserted).
- Added 4 new tests in 2 new TestFromAC_ classes:
  - TestFromAC_ScheduleTaskRetry_IdempotencyGuardHigherAttempt (2 tests): test_guard_skips_when_current_attempt_exceeds_next_attempt, test_guard_skips_produces_no_kanban_call.
  - TestFromAC_ScheduleTaskRetry_KanbanFailureLogging (2 tests): test_kanban_failure_during_exhaustion_logs_warning, test_kanban_failure_during_budget_block_logs_warning.
- Preserved: 31 existing tests, all PASS.
- AC5 gap closed: concurrent write to attempt=3 while guarded call computed next_attempt=2; guard current.attempt > next_attempt fires, state not overwritten.
- AC6 gap closed: logger.warning assert_called_once() with task_id present in call args for both exhaustion and budget paths.
- AC7 note: schedule_task_retry exists since commit 5bf5fd0 (#984); all 35 tests pass. RED-only header is a known artifact.
- ruff: clean.
- Total: 35 tests, all PASS.

[[2026-03-24]] Tue 14:05

## Builder Notes

- Files changed: none
- Tests: 35 passed in tests/test_schedule_task_retry.py
- Coverage: src/owlbear/daemon.py 28% in scoped bare coverage run (module-wide informational metric)
- Lint: ruff check passed for src/owlbear/daemon.py and tests/test_schedule_task_retry.py
- Evidence: pytest file run passed; coverage run passed; ruff run passed
- Fixes applied: None (schedule_task_retry already implemented and all TestFromAC tests were green before this builder pass)

[[2026-03-24]] Tue 14:53

## Review Evidence

### Findings

- No blocking findings.

### Test Results

- pytest tests/test_schedule_task_retry.py: 35 passed, 2 warnings.
- Focused retry-gap tests: 4 passed, 2 warnings.
- Warnings were optional qdrant_client skips only.
- ruff: All checks passed.
- coverage: src/owlbear/daemon.py 28 percent module-wide; reviewed function branches at daemon.py lines 523, 529-530, 539, 542, 548-549, and 557 are covered by task tests.

### Critical Checks

- AC1 covered by TestFromAC classes at tests/test_schedule_task_retry.py lines 46, 237, 348, 479, 618, 890, and 972.
- AC2 covered by scheduling tests; RetryEntry write occurs at src/owlbear/daemon.py line 557.
- AC3 covered by exhaustion tests; block and cleanup occur at src/owlbear/daemon.py lines 542 and 548-549.
- AC4 covered by budget tests, including stale retry cleanup at tests/test_schedule_task_retry.py line 444; budget branch and cleanup occur at src/owlbear/daemon.py lines 523 and 529-530.
- AC5 covered by original idempotency tests plus higher-attempt guard tests at tests/test_schedule_task_retry.py lines 900 and 938; the guard is at src/owlbear/daemon.py line 539.
- AC6 covered by original swallow tests plus logging tests at tests/test_schedule_task_retry.py lines 980 and 1007; warning sites are at src/owlbear/daemon.py lines 528 and 547.
- AC7 covered historically: the task body recorded 21 ImportError failures at 09:24, commit e152655 predates commit 5bf5fd0, and git show e152655:src/owlbear/daemon.py confirmed schedule_task_retry was absent.
- Security review: no issues in src/owlbear/daemon.py lines 506-560.
- Test integrity: current working-tree diff vs HEAD only appends the retry classes at line 883 onward. The original #990 methods were preserved semantically; changes are strengthening only.
- Test quality: assertion specificity STRONG, negative paths STRONG, mutation resistance STRONG, independence STRONG, names STRONG.
- Implementation-aware gaps: none significant.

### Verdict

- PASS
- Confidence: .93

[[2026-03-24]] Tue 15:26

## Docs Gate

### Checklist

No docs impact. Pure TDD RED test task. All checks N/A. Builder reported files changed none.

### Scratch Files Cleaned

docs/scratch/990-ac.tmp, 990-builder-notes.tmp, 990-pytest.txt, 990-tw-retry.tmp deleted.

[[2026-03-24]] Tue 15:52

## Audit

### AC Verification

- AC1 PASS: TestFromAC classes exist in tests/test_schedule_task_retry.py.
- AC2 PASS: 8 scheduling tests verify RetryEntry fields. Scoped run: 38 passed.
- AC3 PASS: 4 exhaustion tests verify kanban block, retries pop, claimed discard.
- AC4 PASS: 5 budget tests verify block call, claimed discard, no RetryEntry, stale cleanup.
- AC5 PASS: Original same-attempt tests plus retry higher-attempt guard tests at lines 954-1033.
- AC6 PASS: Original swallow tests plus retry logging tests at lines 1036-1097 verify logger.warning.
- AC7 PASS: Historical RED evidence (21 ImportError failures) confirmed via git history.

### Test Results

- pytest scoped: 38 passed, 2 warnings.
- pytest full suite: 4235 passed, 39 failed (pre-existing), 20 skipped.
- ruff: All checks passed.

### Architect Quality: 4/5

### Confidence: .96

### Action: archive

## Commits

- b9506af test: add schedule_task_retry standalone tests (#990, auditor)
