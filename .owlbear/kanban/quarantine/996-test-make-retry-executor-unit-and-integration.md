---
id: 996
title: 'Test: make_retry_executor unit and integration tests'
status: archived
priority: needed
created: 2026-03-24T21:50:48.4360835+01:00
updated: 2026-03-25T02:33:34.4822793+01:00
started: 2026-03-25T02:33:11.4121903+01:00
completed: 2026-03-25T02:33:11.4121903+01:00
tags:
    - daemon
    - hooks
    - scope:core
    - type:test
    - test
class: standard
---

## Acceptance Criteria

- [ ] AC1: File `tests/test_retry_executor.py` contains all tests below. Tests import from `owlbear.daemon` and `owlbear.core.hook_reaction_router`.
- [ ] AC2: `test_make_retry_executor_returns_callable` â€” factory returns a callable. Verify with `callable(result)`.
- [ ] AC3: `test_retry_executor_missing_task_id_logs_warning` â€” call executor with `data={}`; assert `caplog` contains a warning-level message; assert `state.retries` is empty.
- [ ] AC4: `test_retry_executor_budget_exceeded_skips` â€” call executor with `data={task_id: 1, outcome: budget_exceeded}`; assert `state.retries` is empty.
- [ ] AC5: `test_retry_executor_failure_schedules_entry` â€” call executor with `data={task_id: 1, outcome: failure, error: boom}`; assert `state.retries[1]` is a `RetryEntry` with `attempt == 1` and `last_error` containing `boom`.
- [ ] AC6: `test_retry_executor_integration_via_hooks` â€” create `HookRegistry` + `HookReactionRouter` with one rule matching `{outcome: failure}` on `TASK_COMPLETE` with action `retry`; wire executor dict with real `make_retry_executor`; emit `TASK_COMPLETE` with failure data; assert `RetryEntry` appears in `state.retries`.
- [ ] AC7: `test_retry_executor_idempotent_with_reconcile` â€” call `schedule_task_retry` directly for task 1 (attempt 1), then fire the hook executor for the same task; assert `state.retries[1].attempt == 1` (second call is no-op due to idempotency).
- [ ] AC8: All tests fail (RED) against the current codebase since `make_retry_executor` does not exist. `ruff check` clean on the test file.

### Architecture Notes

- Mock `KanbanToolset` with `AsyncMock`.
- `OrchestratorState` is a plain dataclass â€” construct directly, no mocking needed.
- For AC6, use real `HookReactionRouter` and `HookRegistry` (no mocking). Create a `HookReactionRule` with `events=[task_complete], actions=[retry], match={outcome: failure}`.
- For AC7, use real `schedule_task_retry` with a mock kanban.

[[2026-03-24]] Tue 22:18

## Test-Writer Notes

- Test file: tests/test_retry_executor.py
- Classes: TestFromAC_RetryExecutorFactory, TestFromAC_RetryExecutorUnit, TestFromAC_RetryExecutorIntegration
- Tests per category: happy 2, edge 1, error 1, boundary 2
- Total: 6 tests, all FAIL (ImportError: make_retry_executor not in owlbear.daemon)
- ruff: clean

[[2026-03-24]] Tue 22:33

## Builder Notes

- Files changed: src/owlbear/daemon.py
- Tests: 6 passed in tests/test_retry_executor.py.
- Coverage: src/owlbear/daemon.py reported 24% in scoped coverage run.
- Lint: ruff clean on src/owlbear/daemon.py and tests/test_retry_executor.py.
- Evidence: RED run failed on ImportError for make_retry_executor. GREEN run passed all 6 AC tests with pytest_asyncio plugin explicitly loaded.
- Fixes applied: Added make_retry_executor factory that warns on missing task_id, ignores non-failure outcomes, and delegates failure scheduling to schedule_task_retry with an idempotent skip when retry state already exists.

[[2026-03-24]] Tue 22:52

## Review Evidence

## Review: #996 - Test: make_retry_executor unit and integration tests

### Findings

1. CRITICAL - The integration coverage misses the real failure payload shape. src/owlbear/daemon.py:665-667 emits TASK_COMPLETE with only task_id and outcome, but src/owlbear/daemon.py:596-597 reads data.get(error) and records RuntimeError(str(error_obj)). A direct reviewer probe calling the executor with {'task_id':'T1','outcome':'failure'} recorded last_error as None. The current tests only cover failure cases with an explicit error field at tests/test_retry_executor.py:78 and 104, so the suite would not catch broken retry diagnostics on the actual daemon path.
2. QUALITY - Editor diagnostics report four compile errors in tests/test_retry_executor.py at lines 59, 73, 86, and 158: object is not awaitable. The new factory is typed as Callable[[dict[str, object]], object], so the awaited executor is statically incompatible in the new test file.

### Test Results

- Scoped pytest on tests/test_retry_executor.py: 6 passed, 0 failed, 2 optional-dependency warnings.
- Adjacent regression slice on existing daemon and router tests: 3 passed, 0 failed.
- Tooling note: foreground pytest startup hung once in tests/conftest.py on Windows; rerun with plugin autoload disabled completed cleanly.

### Lint Results

- Ruff on src/owlbear/daemon.py and tests/test_retry_executor.py: clean.

### Coverage

- Scoped coverage run completed successfully.
- src/owlbear/daemon.py reported 24 percent in the scoped run; this whole-file figure on a large module was not used as the sole gate signal.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 file and imports | Structural check in tests/test_retry_executor.py lines 29, 48, 65, 78, 104, 133 plus imports at 31, 52, 67, 80, 107, 109, 138 | Yes for missing tests or imports; file content verified directly | COVERED |
| AC2 callable factory | TestFromAC_RetryExecutorFactory::test_make_retry_executor_returns_callable | Yes, asserts callable(result) | COVERED |
| AC3 missing task_id warning | TestFromAC_RetryExecutorUnit::test_retry_executor_missing_task_id_logs_warning | Yes, asserts warning and empty retries | COVERED |
| AC4 budget_exceeded skip | TestFromAC_RetryExecutorUnit::test_retry_executor_budget_exceeded_skips | Yes, retries would become non-empty if skip logic broke | COVERED |
| AC5 failure schedules retry | TestFromAC_RetryExecutorUnit::test_retry_executor_failure_schedules_entry | Yes, asserts RetryEntry type, attempt 1, and error text | COVERED |
| AC6 hook router integration | TestFromAC_RetryExecutorIntegration::test_retry_executor_integration_via_hooks | Yes for the explicit payload used by the test | COVERED |
| AC7 idempotent reconcile path | TestFromAC_RetryExecutorIntegration::test_retry_executor_idempotent_with_reconcile | Yes for attempt increment regressions; see test-gap note below | COVERED |
| AC8 RED provenance and clean test lint | Git history shows 375a701 contains only test-file references to make_retry_executor while bbd1238 adds the daemon function; current ruff run is clean | Yes, verified from git history plus lint | COVERED |

#### Security Review

- No security issues found in the added factory.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_make_retry_executor_returns_callable | No change between 375a701 and bbd1238 | PRESERVED |
| test_retry_executor_missing_task_id_logs_warning | No change between 375a701 and bbd1238 | PRESERVED |
| test_retry_executor_budget_exceeded_skips | No change between 375a701 and bbd1238 | PRESERVED |
| test_retry_executor_failure_schedules_entry | No change between 375a701 and bbd1238 | PRESERVED |
| test_retry_executor_integration_via_hooks | No change between 375a701 and bbd1238 | PRESERVED |
| test_retry_executor_idempotent_with_reconcile | No change between 375a701 and bbd1238 | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Failure test checks RetryEntry type, attempt, and error text. Integration test asserts actual RetryEntry creation through HookReactionRouter. |
| Negative and error paths | ADEQUATE | Missing task_id and budget_exceeded cases are covered. |
| Mutation reasoning | WEAK | The suite never exercises a failure payload without an error key, even though the surrounding daemon hook path emits only task_id and outcome. A broken executor records last_error as None and all current tests still pass. |
| Test independence | STRONG | Each test builds fresh OrchestratorState and AsyncMock instances. |
| Descriptive names | STRONG | Test names clearly describe scenario and expected behavior. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- Significant gap found: the actual daemon failure hook path emits {task_id: tid, outcome: outcome} at src/owlbear/daemon.py:665-667 with no error field, but make_retry_executor reads data.get(error) and falls back to RuntimeError(str(error_obj)) at src/owlbear/daemon.py:596-597. Direct reviewer probe of the current implementation with {'task_id':'T1','outcome':'failure'} recorded last_error as None.
- The current AC-driven tests cover explicit error-bearing payloads only at tests/test_retry_executor.py:78 and 104, so they would not catch this real-path diagnostic regression.

### Pass 2 - INFORMATIONAL

- tests/test_retry_executor.py has editor diagnostics at lines 59, 73, 86, and 158: object is not awaitable.
- No documentation or structure findings beyond the issues above.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | tests/test_retry_executor.py contains the six named tests at lines 29, 48, 65, 78, 104, 133 and imports from owlbear.daemon and HookReactionRouter at 31, 52, 67, 80, 107, 109, 138 | Structural verification | PASS |
| AC2 | pytest passed test_make_retry_executor_returns_callable; make_retry_executor exists at src/owlbear/daemon.py:569 | test_make_retry_executor_returns_callable | PASS |
| AC3 | pytest passed test_retry_executor_missing_task_id_logs_warning; warning branch at src/owlbear/daemon.py:582 | test_retry_executor_missing_task_id_logs_warning | PASS |
| AC4 | pytest passed test_retry_executor_budget_exceeded_skips; non-failure skip branch at src/owlbear/daemon.py:589 | test_retry_executor_budget_exceeded_skips | PASS |
| AC5 | pytest passed test_retry_executor_failure_schedules_entry; scheduler call at src/owlbear/daemon.py:598 | test_retry_executor_failure_schedules_entry | PASS |
| AC6 | pytest passed test_retry_executor_integration_via_hooks; HookReactionRouter import at tests/test_retry_executor.py:107 | test_retry_executor_integration_via_hooks | PASS |
| AC7 | pytest passed test_retry_executor_idempotent_with_reconcile; idempotent branch at src/owlbear/daemon.py:593 | test_retry_executor_idempotent_with_reconcile | PASS |
| AC8 | git history shows 375a701 had no daemon definition for make_retry_executor, builder diff adds the function, and current ruff run is clean | Historical provenance and current lint | PASS |

### Verdict: FAIL

### Action Taken

- Appended review evidence.
- Returned task to todo for rework because the current tests miss a significant real-path failure case and the new test file has static diagnostics.

[[2026-03-24]] Tue 23:08

## Test-Writer Notes (retry)

- Retry reason: reviewer CRITICAL cited untested daemon-order path (hook fires without error field, then direct schedule_task_retry fires — double-scheduling increments attempt to 2 instead of 1).
- Added: 1 new failing test: TestFromAC_RetryExecutorIntegration::test_retry_executor_daemon_order_does_not_double_schedule
- Asserts: attempt==1 and last_error contains 'actual error' after hook+direct dual-fire
- Preserved: 6 existing tests (all PASS)
- ruff: clean
- pytest: 1 FAIL (AssertionError: assert 2 == 1), 6 PASS

[[2026-03-24]] Tue 23:22

## Builder Notes

- Files changed: src/owlbear/daemon.py
- Tests: 7 passed in tests/test_retry_executor.py.
- Coverage: scoped run reported src/owlbear/daemon.py at 24 percent; this reflects whole-file coverage on a large module.
- Lint: ruff clean on src/owlbear/daemon.py and tests/test_retry_executor.py.
- Evidence: RED baseline had 1 failing test, test_retry_executor_daemon_order_does_not_double_schedule, with attempt 2 instead of expected 1. GREEN rerun passed all 7 tests.
- Fixes applied: make_retry_executor now skips hook-side scheduling when payload has no error field so reconcile direct scheduling remains the single source of retry creation. Updated factory return type to an awaitable callable to remove awaitability diagnostics.

[[2026-03-25]] Wed 00:23

## Review Evidence

## Review: #996 - Test: make_retry_executor unit and integration tests

### Findings

1. CRITICAL: AC6 remains unverified against the real TASK_COMPLETE payload contract. TaskCompleteData only defines task_id and outcome at src/owlbear/core/hooks.py:122,131-132, and reconcile emits exactly {task_id: tid, outcome: outcome} at src/owlbear/daemon.py:672. The AC6 test injects a non-contract error field at tests/test_retry_executor.py:126, while make_retry_executor now skips hook-side scheduling when error is absent at src/owlbear/daemon.py:597-603. A direct reviewer probe through HookRegistry plus HookReactionRouter with the real payload shape printed {} for state.retries, so the current suite would still pass even though the actual hook-only integration path produces no RetryEntry.
2. CRITICAL: The retry-cycle test does not compensate for that gap. The new test documents the real daemon payload at tests/test_retry_executor.py:183 and claims the no-error hook call seeds RetryEntry attempt 1 at tests/test_retry_executor.py:168-169, but it never asserts on state after the hook call. The test passes today because the hook executor is effectively a no-op for that payload and the later direct schedule_task_retry call creates attempt 1 by itself.

### Test Results

- Scoped pytest on tests/test_retry_executor.py: 7 passed, 0 failed.
- Adjacent retry and reconcile regression slice: 49 passed, 0 failed.
- Hook router and bootstrap regression slice: 72 passed, 0 failed.
- Unrelated pre-existing tooling note: tests/test_957_notify_escalate_executors.py still aborts collection with ImportError for _make_escalate_executor.

### Lint Results

- Ruff is clean for src/owlbear/daemon.py, tests/test_retry_executor.py, tests/test_schedule_task_retry.py, and tests/test_daemon_coverage_gaps.py.
- Editor diagnostics report no errors in src/owlbear/daemon.py or tests/test_retry_executor.py.

### Coverage

- Scoped coverage run completed successfully.
- src/owlbear/daemon.py reported 24 percent in the scoped run; this whole-file figure on a large module was not used as the gate signal.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 file and imports | Structural verification at tests/test_retry_executor.py:29,48,65,78,104,133,163 plus imports at 31,52,67,80,107,109,135,173 | Yes for missing tests or imports | COVERED |
| AC2 callable factory | TestFromAC_RetryExecutorFactory::test_make_retry_executor_returns_callable | Yes, asserts callable(result) | COVERED |
| AC3 missing task_id warning | TestFromAC_RetryExecutorUnit::test_retry_executor_missing_task_id_logs_warning | Yes, asserts warning and empty retries | COVERED |
| AC4 budget_exceeded skip | TestFromAC_RetryExecutorUnit::test_retry_executor_budget_exceeded_skips | Yes, retries stay empty | COVERED |
| AC5 failure schedules entry | TestFromAC_RetryExecutorUnit::test_retry_executor_failure_schedules_entry | Yes, asserts RetryEntry type, attempt 1, and error text | COVERED |
| AC6 hook router integration | TestFromAC_RetryExecutorIntegration::test_retry_executor_integration_via_hooks | No. It passes only with a fabricated error key at tests/test_retry_executor.py:126; the real TASK_COMPLETE contract is task_id plus outcome only at src/owlbear/core/hooks.py:122,131-132 and src/owlbear/daemon.py:672 | LAX |
| AC7 idempotent with reconcile | TestFromAC_RetryExecutorIntegration::test_retry_executor_idempotent_with_reconcile | Yes for pre-existing retry entry path | COVERED |
| AC8 RED provenance and test-file lint | Git history shows 375a701 added RED tests before implementation commits bbd1238 and a89d688; current ruff run is clean | Yes | COVERED |

#### Security Review

- No security issues found in the added factory.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Six original TestFromAC methods from 375a701 | Present unchanged in current file | PRESERVED |
| Retry-cycle addition from bf9f092 | Present unchanged in current file; builder diff from bf9f092 to HEAD is empty for tests/test_retry_executor.py | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC2 through AC5 and AC7 make concrete assertions on retries, attempt counts, and error text |
| Negative and error paths | ADEQUATE | Missing task_id and budget_exceeded are covered |
| Mutation reasoning | WEAK | The suite still passes while the real hook-only TASK_COMPLETE payload path yields empty retries; the AC6 test hides this with a non-contract payload and the retry-cycle test never checks state after the hook call |
| Test independence | STRONG | Fresh OrchestratorState and AsyncMock instances per test |
| Descriptive names | STRONG | Test names clearly describe the scenarios |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- Significant gap remains in the real hook-router path. HookReactionRouter passes the emitted payload straight to the executor at src/owlbear/core/hook_reaction_router.py:88,93-94. The daemon emits TASK_COMPLETE failure data as only task_id and outcome at src/owlbear/daemon.py:671-672, while make_retry_executor returns early when error is absent at src/owlbear/daemon.py:597-603. Reviewer probe with HookRegistry plus HookReactionRouter and payload {task_id: 42, outcome: failure} left state.retries as {}.
- The retry-cycle test at tests/test_retry_executor.py:163-199 is not compensating coverage because it does not assert whether the hook-side call created or mutated retry state before the direct schedule_task_retry call.

### Pass 2 - INFORMATIONAL

- The test description at tests/test_retry_executor.py:168-169 no longer matches the behavior under review; the executor does not seed RetryEntry for the real no-error daemon payload.
- No additional code structure or documentation findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | File contains the expected tests and imports from owlbear.daemon and HookReactionRouter | Structural verification | PASS |
| AC2 | pytest passed callable factory test; make_retry_executor is defined at src/owlbear/daemon.py:569 | test_make_retry_executor_returns_callable | PASS |
| AC3 | pytest passed warning-path test; warning log branch at src/owlbear/daemon.py:582 | test_retry_executor_missing_task_id_logs_warning | PASS |
| AC4 | pytest passed budget_exceeded skip test; non-failure return at src/owlbear/daemon.py:589 | test_retry_executor_budget_exceeded_skips | PASS |
| AC5 | pytest passed failure scheduling test; schedule_task_retry call at src/owlbear/daemon.py:603 | test_retry_executor_failure_schedules_entry | PASS |
| AC6 | Current test uses non-contract payload with error field at tests/test_retry_executor.py:126. Real TASK_COMPLETE payload is only task_id and outcome at src/owlbear/core/hooks.py:122,131-132 and src/owlbear/daemon.py:672, and reviewer probe through HookRegistry with that payload produced empty retries | test_retry_executor_integration_via_hooks | FAIL |
| AC7 | pytest passed idempotent existing-retry test; state.retries guard at src/owlbear/daemon.py:593 | test_retry_executor_idempotent_with_reconcile | PASS |
| AC8 | Git history shows RED then GREEN progression and current ruff run is clean | Historical provenance and lint | PASS |

### Verdict: FAIL

### Action Taken

- Appended review evidence.
- Returning task to todo for rework.

[[2026-03-25]] Wed 01:28

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL (2nd cycle) -- AC6 FAIL in compliance table: existing test used non-contract payload (error field not in TaskCompleteData), and retry-cycle test had no intermediate-state assertion.
- Added: 2 new failing tests in TestFromAC_RetryExecutorRealPayload
- test_retry_executor_integration_real_daemon_payload: emits real {task_id, outcome} through HookRegistry, asserts RetryEntry created. FAILS: AssertionError (state.retries == {}).
- test_retry_executor_hook_seeds_entry_before_reconcile: fires executor with no-error payload, asserts intermediate state exists (attempt=1) before direct schedule. FAILS: AssertionError hook executor must seed RetryEntry.
- Preserved: 7 existing tests (all PASS)
- ruff: clean
- pytest: 2 FAIL, 7 PASS

[[2026-03-25]] Wed 01:46

## Builder Notes

- Files changed: src/owlbear/daemon.py
- Tests: tests/test_retry_executor.py passed 9; tests/test_schedule_task_retry.py passed 38
- Coverage: scoped run reports src/owlbear/daemon.py at 24 percent
- Lint: ruff check clean for src/owlbear/daemon.py and tests/test_retry_executor.py
- Evidence: red phase had 2 failing real-payload tests; green phase passed all 9 in retry executor suite
- Fixes applied: make_retry_executor now schedules retry for failure payloads without explicit error; schedule_task_retry preserves attempt 1 for that hook-seeded entry and replaces placeholder error text with reconcile exception text
- Commit: 8e4abbe

[[2026-03-25]] Wed 01:59

## Review Evidence

## Review: #996 - Test: make_retry_executor unit and integration tests

### Findings

- No blocking findings.

### Test Results

- tests/test_retry_executor.py: 9 passed, 2 expected optional-dependency warnings.
- tests/test_schedule_task_retry.py: 38 passed, 2 expected optional-dependency warnings.
- tests/test_hook_reaction_router.py: 35 passed, 2 expected optional-dependency warnings.
- Broader hook-path regression batch across tests/test_hook_reaction_router.py, tests/test_hook_payloads.py, and tests/test_955_hook_reaction_schema_bootstrap.py reported 101 passed and 2 failed. Both failures were unrelated pre-existing checks in tests/test_hook_payloads.py for PreToolUseData missing from owlbear.core.__all__. Task #996 only changes src/owlbear/daemon.py.
- Editor diagnostics: no errors in src/owlbear/daemon.py or tests/test_retry_executor.py.

### Lint Results

- Ruff passed on src/owlbear/daemon.py, tests/test_retry_executor.py, and tests/test_schedule_task_retry.py.

### Coverage

- Scoped coverage run over tests/test_retry_executor.py and tests/test_schedule_task_retry.py: 47 passed.
- src/owlbear/daemon.py reported 31 percent in the scoped run. This whole-file figure on a large module was not used as the sole gate signal.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1 file and imports | Structural verification in tests/test_retry_executor.py at 11, 29, 48, 65, 78, 104, 133, 163, 219, 255, plus imports at 31, 107, and 227 | Yes. Missing tests or wrong imports would fail direct file inspection. | COVERED |
| AC2 callable factory | TestFromAC_RetryExecutorFactory::test_make_retry_executor_returns_callable | Yes. Asserts callable(result) at line 36. | COVERED |
| AC3 missing task_id warning | TestFromAC_RetryExecutorUnit::test_retry_executor_missing_task_id_logs_warning | Yes. Asserts warning log and empty retry state at 61 and 62. | COVERED |
| AC4 budget_exceeded skip | TestFromAC_RetryExecutorUnit::test_retry_executor_budget_exceeded_skips | Yes. Retries remain empty at line 75 when outcome is not failure. | COVERED |
| AC5 failure schedules entry | TestFromAC_RetryExecutorUnit::test_retry_executor_failure_schedules_entry | Yes. Asserts RetryEntry type, attempt 1, and error text at 90, 91, and 92. | COVERED |
| AC6 hook router integration | TestFromAC_RetryExecutorIntegration::test_retry_executor_integration_via_hooks plus TestFromAC_RetryExecutorRealPayload::test_retry_executor_integration_real_daemon_payload | Yes. The real-payload test emits only task_id and outcome at line 247, matching TaskCompleteData at src/owlbear/core/hooks.py 131 and 132 and reconcile_tasks emit payload at src/owlbear/daemon.py 679, and asserts RetryEntry creation at 251 and 252. | COVERED |
| AC7 idempotent with reconcile | TestFromAC_RetryExecutorIntegration::test_retry_executor_idempotent_with_reconcile plus the daemon-order and hook-seed tests at 163 and 255 | Yes. Existing-retry no-op is asserted at 154 and 160, hook-first ordering keeps attempt 1 and preserves the real error at 199 and 200, and the intermediate hook-seed assertion is pinned at 280, 281, and 295. | COVERED |
| AC8 RED provenance and clean test lint | Git history plus current lint | Yes. git grep found no make_retry_executor definition before the RED test commit, first implementation appears in bbd1238, both RED commits 375a701 and d2eac84 touch only tests/test_retry_executor.py, and current Ruff is clean. | COVERED |

#### Security Review

- No security issues found. The change only adjusts in-memory retry bookkeeping on the existing hook path and does not add shell, filesystem, deserialization, or secret-handling surface.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_make_retry_executor_returns_callable | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_missing_task_id_logs_warning | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_budget_exceeded_skips | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_failure_schedules_entry | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_integration_via_hooks | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_idempotent_with_reconcile | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_daemon_order_does_not_double_schedule | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_integration_real_daemon_payload | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |
| test_retry_executor_hook_seeds_entry_before_reconcile | No change. git diff d2eac84..8e4abbe for tests/test_retry_executor.py is empty. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Tests assert callable(result), empty retry state, warning logs, RetryEntry type, attempt counts, and error text at 36, 61, 62, 90 to 92, 129, 130, 199, 200, 251, 252, 280, 281, and 295. |
| Negative and error paths | STRONG | Missing task_id, budget_exceeded, real failure with explicit error, real daemon payload without error, existing-retry idempotency, and hook-first ordering are all exercised. |
| Mutation reasoning | STRONG | Removing placeholder seeding at src/owlbear/daemon.py 608, removing placeholder replacement at 542 to 547, or removing the existing-retry guard at 605 would fail the real-payload and daemon-order tests. |
| Test independence | STRONG | Each test constructs fresh OrchestratorState and AsyncMock instances; no shared mutable state or order dependency is visible in the file. |
| Descriptive names | STRONG | The test names are scenario-specific and map directly to the acceptance criteria and prior review findings. |

#### Data Safety

- No data safety issues found. The touched code only mutates existing in-memory retry state and keeps the retry write path idempotent for same-attempt callers.

#### Implementation-Aware Test Gaps

- No significant untested paths found in the touched logic. The reviewed suite covers missing task_id, non-failure outcomes, explicit error failures, real TASK_COMPLETE payloads without error, pre-existing retry idempotency, hook-first reconcile ordering, and placeholder-error replacement in schedule_task_retry.

### Pass 2 - INFORMATIONAL

- Broader hook-path regression work still shows unrelated pre-existing failures in tests/test_hook_payloads.py around owlbear.core.__all__ exports. These do not intersect the #996 diff.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | tests/test_retry_executor.py contains the required test cases and imports from owlbear.daemon and owlbear.core.hook_reaction_router at 11, 31, 107, and 227 | Structural verification | PASS |
| AC2 | make_retry_executor is defined at src/owlbear/daemon.py 581, returns _executor at 620, and test_make_retry_executor_returns_callable passed with callable(result) asserted at 36 | test_make_retry_executor_returns_callable | PASS |
| AC3 | Missing task_id warning branch is at src/owlbear/daemon.py 594 and the test asserts warning plus empty retries at 61 and 62 | test_retry_executor_missing_task_id_logs_warning | PASS |
| AC4 | Non-failure skip branch is at src/owlbear/daemon.py 601 and the budget_exceeded test asserts retries stay empty at 75 | test_retry_executor_budget_exceeded_skips | PASS |
| AC5 | make_retry_executor delegates to schedule_task_retry at src/owlbear/daemon.py 610, schedule_task_retry writes RetryEntry at 573, and the failure test asserts type, attempt, and error text at 90 to 92 | test_retry_executor_failure_schedules_entry | PASS |
| AC6 | TaskCompleteData contract is task_id and outcome only at src/owlbear/core/hooks.py 131 and 132, reconcile_tasks emits exactly that payload at src/owlbear/daemon.py 679, HookReactionRouter awaits coroutine executors at src/owlbear/core/hook_reaction_router.py 94 and 95, and the real-payload integration test emits that shape at 247 and asserts RetryEntry creation at 251 and 252 | test_retry_executor_integration_real_daemon_payload | PASS |
| AC7 | Existing-retry idempotency guard is at src/owlbear/daemon.py 605 and placeholder replacement path is at 542 to 547; the tests assert attempt stays 1 in the direct-first path at 154 and 160 and in the hook-first path at 199, 200, 280, 281, and 295 | test_retry_executor_idempotent_with_reconcile, test_retry_executor_daemon_order_does_not_double_schedule, test_retry_executor_hook_seeds_entry_before_reconcile | PASS |
| AC8 | RED provenance is verified by git history: 375a701 and d2eac84 are test-only commits, git grep finds the first make_retry_executor definition at bbd1238, and current Ruff is clean on the task files | Historical provenance and current lint | PASS |

### Verdict: PASS

### Action Taken

- Moved task 996 from review to docs and released the reviewer claim.

[[2026-03-25]] Wed 02:05

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Named make_retry_executor in Runtime row; existing entry said only 'real executors from #956 (retry)'; now includes factory name and #996 reference |
| 2 | Docstrings | Yes | Pass | make_retry_executor has docstring at daemon.py:581. RetryEntry and schedule_task_retry have existing docstrings. |
| 3 | docs/sources/overview.md | No | N/A | No external patterns introduced |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase |

### Files Updated

- .github/copilot-instructions.md

### Scratch Files Cleaned

- docs/scratch/996-builder-notes.tmp

[[2026-03-25]] Wed 02:33

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 file and imports | tests/test_retry_executor.py exists with 9 tests, imports from owlbear.daemon and owlbear.core.hook_reaction_router | PASS |
| AC2 callable factory | test_make_retry_executor_returns_callable at L29, make_retry_executor at daemon.py:581 | PASS |
| AC3 missing task_id warning | test at L48, warning branch at daemon.py:594 | PASS |
| AC4 budget_exceeded skip | test at L65, non-failure return at daemon.py:601 | PASS |
| AC5 failure schedules entry | test at L78, RetryEntry created via schedule_task_retry at daemon.py:610 | PASS |
| AC6 hook router integration | Original test at L104 plus real-payload tests at L219/L255; real TASK_COMPLETE shape verified. 3 reviewer cycles confirmed contract correctness | PASS |
| AC7 idempotent reconcile | Tests at L133, L163, L255 cover both orderings (direct-first and hook-first). Placeholder error replacement at daemon.py:542-547 | PASS |
| AC8 RED provenance and lint | git log shows RED commits 375a701, bf9f092, d2eac84 precede GREEN commits bbd1238, a89d688, 8e4abbe. ruff clean | PASS |

### Test Results

- pytest (scoped): 9 passed, 0 failed
- pytest (full suite): 4187 passed, 163 failed (all pre-existing), 20 skipped
- ruff: clean on src/owlbear/daemon.py and tests/test_retry_executor.py

### Upstream Commits Verified

- 375a701 test: add failing tests for make_retry_executor (#996, test-writer)
- bbd1238 feat: implement retry hook executor (#996, builder)
- bf9f092 test: add daemon-order double-schedule failing test (#996, test-writer)
- a89d688 fix: prevent retry double-schedule in hook path (#996, builder)
- d2eac84 test: add failing tests for real-payload contract (#996, test-writer)
- 8e4abbe fix: handle real hook retry payload idempotently (#996, builder)
- 101b4c1 docs: name make_retry_executor in tech stack (#996, writer)

### Reviewer Evidence

3rd-cycle review (final PASS) was thorough: all AC lines mapped with evidence, test integrity verified via git diff, test quality rated STRONG across all dimensions, no implementation-aware gaps found.

### AC Quality Score: 4/5

AC was specific and led to clean TDD cycles. One gap (real TASK_COMPLETE payload contract vs. synthetic error field) required two reviewer rejection cycles. The AC should have specified the real payload shape explicitly. Architecture notes were productive.

### Confidence: .97

### Action: archive

[[2026-03-25]] Wed 02:33

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8db650c | chore | kanban/tasks/996-*.md | #996 |
