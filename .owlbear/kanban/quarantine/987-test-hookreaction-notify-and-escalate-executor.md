---
id: 987
title: 'Test: HookReaction notify and escalate executor wiring'
status: archived
priority: important
created: 2026-03-24T04:26:51.0818483+01:00
updated: 2026-03-25T17:09:45.5784234+01:00
started: 2026-03-25T17:09:04.1461689+01:00
completed: 2026-03-25T17:09:04.1461689+01:00
tags:
    - agent
    - hooks
    - scope:core
    - type:test
    - test
depends_on:
    - 955
class: standard
---

RED tests for #957. Verify real notify and escalate executor factories produce correct behavior when wired through HookReactionRouter in build_hooks().

## Acceptance Criteria

- [ ] AC1: A `_make_notify_executor(backends)` factory in `bootstrap/hooks.py` returns an Executor that iterates backends in declared order, stopping on the first success (returns `True`); assert first-success short-circuit and that all backends are tried when all fail.
- [ ] AC2: A `_make_escalate_executor(channel)` factory in `bootstrap/hooks.py` returns an Executor that calls `channel.send()` with a formatted escalation message containing the event name and payload summary; assert send is called exactly once and message contains the triggering event.
- [ ] AC3: When `channel is None` and escalate action is configured, `build_hooks()` logs a warning and uses a noop escalate executor; assert log emission and noop behavior.
- [ ] AC4: When a notify backend raises, the executor catches the exception, logs a warning, and continues to the next backend (failure isolation); assert the chain continues and no exception propagates.
- [ ] AC5: The escalate executor does NOT catch exceptions from `channel.send()` â€” exceptions propagate to the caller (consistent with #957 AC2). Test that calling the factory-returned executor directly with a mock channel whose `send()` raises causes the exception to propagate. Router-level error swallowing is already tested in #955 and need not be retested here.
- [ ] AC6: `build_hooks()` wires the real executors (not noop) for notify and escalate when `settings.hook_reactions` is non-empty; assert the executors dict values are not the same noop function.
- [ ] AC7: retry executor remains noop when `settings.hook_reactions` is non-empty; assert the retry entry in the executors dict is a noop.
- [ ] AC8: Test file: `tests/test_957_notify_escalate_executors.py`. All tests use `TestFromAC_` class prefix. Tests must FAIL (RED) before implementation.
- [ ] AC9: ruff clean on the test file.

[[2026-03-24]] Tue 04:46

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |

|---------|------------|--------|

| AC1 notify first-success chain | Testable: mock backends, assert call order and short-circuit | Keep |

| AC2 escalate channel.send | Testable: mock channel, assert send call and message content | Keep |

| AC3 channel-None noop fallback | Testable: caplog + build_hooks() with channel=None | Keep |

| AC4 notify per-backend isolation | Testable: raising mock backend, assert continuation | Keep |

| AC6 real executors wired | Testable: monkeypatch HookReactionRouter to capture executors dict | Keep |

| AC7 retry stays noop | Same approach as AC6 | Keep |

| AC8-9 file/prefix/ruff | Mechanical | Keep |

### Architecture Notes

- Module layering: bootstrap/hooks.py is assembly layer, imports from core/ and channels/ are allowed. No violation.

- AC5 was inconsistent with #957 AC2 (escalate executor propagates exceptions to router). Rewritten for consistency.

- Dependency #955 archived. TDD chain: 955 -> 987 (RED) -> 957 (GREEN) correct.

- Test patterns: tests/test_955_hook_reaction_schema_bootstrap.py provides precedent for build_hooks() wiring tests.

### Changes Made

- Rewrote AC5 to match #957 AC2 contract (executor propagates exceptions, router handles isolation).

### Dependencies

- Verified: #955 (HookReaction policy) - archived. #957 depends_on this task - correct TDD ordering.

[[2026-03-25]] Wed 09:15

## Builder Notes

- Files changed: src/owlbear/bootstrap/hooks.py
- Tests: 15 passed in tests/test_957_notify_escalate_executors.py
- Coverage: 94% on src/owlbear/bootstrap/hooks.py from scoped coverage run (exit code 0)
- Lint: ruff clean on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py
- Evidence: RED import error reproduced before implementation; GREEN run reported 15 passed; coverage report lists src/owlbear/bootstrap/hooks.py at 94%; ruff reported all checks passed
- Fixes applied: Added _make_notify_executor and_make_escalate_executor factories; wired build_hooks notify and escalate to real executors when available; kept retry as noop; added channel-none escalate warning fallback

[[2026-03-25]] Wed 11:23

## Review Evidence

### Test Results

- Scoped pytest on tests/test_957_notify_escalate_executors.py: 15 passed in 2.40s.
- Task-scoped ruff check passed and ruff format check reported both files already formatted.
- Scoped coverage run reports src/owlbear/bootstrap/hooks.py at 94%.

### Critical Findings

- FAIL: src/owlbear/bootstrap/hooks.py line 109, line 119, and line 122 log the escalation warning for any non-empty hook_reactions when no channel is provided. A notify-only settings object still emitted the escalation warning, so the warning is not limited to the AC3 condition. tests/test_957_notify_escalate_executors.py line 215 and line 227 cover only the positive escalate-without-channel case; there is no negative test for notify-only plus no channel.
- FAIL: tests/test_957_notify_escalate_executors.py is untracked. Builder commit c7401c3 lists only src/owlbear/bootstrap/hooks.py, scoped git status reports ?? tests/test_957_notify_escalate_executors.py, and git tracking lookup fails for the test file.

### Verdict

FAIL

[[2026-03-25]] Wed 11:23

## Review Evidence - Scoped pytest on tests/test_957_notify_escalate_executors.py passed: 15 passed in 2.40s. Ruff check passed and format check reported both files already formatted. Scoped coverage reports src/owlbear/bootstrap/hooks.py at 94%. FAIL: src/owlbear/bootstrap/hooks.py lines 109, 119, and 122 log the escalation warning for any non-empty hook_reactions when no channel is provided; a notify-only settings object still emitted that warning, and tests/test_957_notify_escalate_executors.py lines 215 and 227 cover only the positive escalate-without-channel case. FAIL: tests/test_957_notify_escalate_executors.py is untracked; builder commit c7401c3 lists only src/owlbear/bootstrap/hooks.py, scoped git status reports ?? tests/test_957_notify_escalate_executors.py, and git tracking lookup fails for the test file. Verdict: FAIL

[[2026-03-25]] Wed 12:03

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL cited missing negative test (notify-only + channel=None must not emit escalation warning)
- Test file: tests/test_957_notify_escalate_executors.py
- Classes: TestFromAC_987_NotifyExecutorFactory, TestFromAC_987_EscalateExecutorFactory, TestFromAC_987_BuildHooksNoneChannelEscalate, TestFromAC_987_BuildHooksExecutorWiring
- Added: 1 new failing test (test_no_warning_when_channel_none_but_no_escalate_action)
- Preserved: 15 existing tests (all PASS)
- FAIL: AssertionError - warning fires for notify-only settings when channel=None
- ruff: clean

[[2026-03-25]] Wed 13:31

## Builder Notes

- Files changed: src/owlbear/bootstrap/hooks.py; tests/test_957_notify_escalate_executors.py
- Tests: 16 passed in tests/test_957_notify_escalate_executors.py
- Coverage: 94 percent on src/owlbear/bootstrap/hooks.py from scoped coverage run
- Lint: ruff check passed on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py
- Evidence: RED run had 1 failing test for notify-only warning condition; GREEN run reported 16 passed in 3.16s; coverage run reported 16 passed in 8.19s and hooks.py at 94 percent; ruff reported All checks passed
- Fixes applied: Restricted escalation warning logging to cases where escalate action is configured and channel is missing
- Commit: a0e0358

[[2026-03-25]] Wed 13:54

## Review Evidence

### Review: #987 - Test: HookReaction notify and escalate executor wiring

### Test Results

- pytest: 16 passed, 0 failed on tests/test_957_notify_escalate_executors.py.
- Related constraint slice: 37 passed, 0 failed on tests/test_955_hook_reaction_schema_bootstrap.py.
- Tooling gap: a targeted tests/test_bootstrap.py build_hooks slice hit the known Windows logfire and pydantic startup KeyboardInterrupt before collection, so that run is not used as verdict evidence.

### Lint Results

- ruff: clean on tests/test_957_notify_escalate_executors.py and src/owlbear/bootstrap/hooks.py.

### Coverage

- src/owlbear/bootstrap/hooks.py: 94 percent in the scoped coverage run.
- Note: pytest-cov emitted a whole-repo table; this review relies only on the touched-module row.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 COVERED: tests/test_957_notify_escalate_executors.py lines 62, 74, and 84 verify first-success short-circuit, all-fail traversal, and declared-order execution.
- AC2 COVERED: lines 156, 167, and 180 verify single send, event-name inclusion, and payload presence in the escalation message.
- AC3 COVERED: lines 218, 227, and 249 verify warning emission for escalate-without-channel, noop fallback wiring, and no false-positive warning for notify-only reactions.
- AC4 LAX: lines 108 and 119 verify continuation and exception isolation, but line 138 only asserts that some warning exists. src/owlbear/bootstrap/hooks.py logs a backend-failure warning at line 50 and a generic all-backends-failed warning at line 57. Removing the exception-path warning would still satisfy the current assertion.
- AC5 COVERED: line 194 verifies that channel.send exceptions propagate to the caller.
- AC6 LAX: lines 239, 244, 294, and 299 capture the executors dict and inspect **qualname** strings, but never invoke the build_hooks-wired notify or escalate callables. A differently named noop function would satisfy the current assertions while violating the real-executor requirement.
- AC7 COVERED: line 329 verifies the retry entry remains the noop placeholder.
- AC8 COVERED: the file path is tests/test_957_notify_escalate_executors.py, every class uses the TestFromAC_prefix, and the retry-added negative test at line 249 is proven RED-before-fix by builder diff a0e0358, which adds the escalate_configured guard at src/owlbear/bootstrap/hooks.py lines 119 through 125.
- AC9 COVERED: task-scoped ruff is clean.

#### Security Review

- No security issues found. The task adds tests plus a narrow warning-scope fix in bootstrap wiring. No shell, SQL, filesystem, or secret-handling surface is introduced.

#### Test Integrity

- Builder commit a0e0358 changed src/owlbear/bootstrap/hooks.py and only reformatted an existing list comprehension in tests/test_957_notify_escalate_executors.py. No TestFromAC assertion was weakened or removed.

#### Test Quality

- Assertion specificity: WEAK. tests/test_957_notify_escalate_executors.py line 138 accepts any warning record, and lines 244, 294, and 329 rely on **qualname** string checks instead of behavior.
- Negative and error paths: STRONG. The suite covers all-fail notify, backend exception isolation, escalate propagation, missing-channel warning, and notify-only no-warning behavior.
- Mutation reasoning: WEAK. Deleting the backend-exception warning at src/owlbear/bootstrap/hooks.py line 50 still leaves the generic warning at line 57, so AC4 stays green. Replacing the build_hooks-wired notify or escalate executor with a differently named noop also leaves AC6 green because the captured callables are never executed.
- Test independence: STRONG. Each test creates isolated mocks and patches.
- Descriptive names: STRONG. Method names state the scenario and expected outcome clearly.

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- The build_hooks wiring tests do not execute the captured notify or escalate executor callables, so the assembly layer is not proven to wire working factory outputs rather than merely non-_noop-named functions.
- The backend-failure warning path is not distinguished from the generic all-backends-failed warning path.

### Pass 2 - INFORMATIONAL

- No informational findings beyond the critical test gaps above.

### AC Compliance

- AC1 PASS: src/owlbear/bootstrap/hooks.py line 47 plus tests/test_957_notify_escalate_executors.py lines 62, 74, and 84.
- AC2 PASS: src/owlbear/bootstrap/hooks.py lines 67 and 68 plus tests/test_957_notify_escalate_executors.py lines 156, 167, and 180.
- AC3 PASS: src/owlbear/bootstrap/hooks.py lines 119 through 125 plus tests/test_957_notify_escalate_executors.py lines 218, 227, and 249.
- AC4 FAIL: src/owlbear/bootstrap/hooks.py lines 49 through 57 are only partially enforced by tests/test_957_notify_escalate_executors.py lines 108, 119, and 138.
- AC5 PASS: src/owlbear/bootstrap/hooks.py line 68 plus tests/test_957_notify_escalate_executors.py line 194.
- AC6 FAIL: src/owlbear/bootstrap/hooks.py lines 114 through 125 are only checked via captured callable names at tests/test_957_notify_escalate_executors.py lines 239, 244, 294, and 299.
- AC7 PASS: src/owlbear/bootstrap/hooks.py line 116 plus tests/test_957_notify_escalate_executors.py line 329.
- AC8 PASS: file and class naming are correct, and the retry negative test is demonstrably red against the pre-fix branch in builder diff a0e0358.
- AC9 PASS: task-scoped ruff returned clean.

### Verdict: FAIL

- Confidence .85. The retry fixes closed the earlier warning-scope bug, but AC4 and AC6 are still too permissive to trust as a TDD contract.

### Action Taken

- Appended review evidence to task #987.
- Returning the task to todo for tighter AC4 and AC6 assertions.

[[2026-03-25]] Wed 14:08

## Test-Writer Notes (retry-2)\n- Overtaken RED: builder landed fix commit a0e0358 before this retry slot ran.\n- Both reviewer FAILs resolved: negative test added (commit 46febf4), file tracked, warning scoped.\n- 16 tests, all PASS (green-on-arrival, no fabricated failures per policy).\n- ruff: clean\n- Advancing to in-progress per green-on-arrival policy

[[2026-03-25]] Wed 14:33

## Builder Notes

- Build mode: Green on arrival for retry-2; TestFromAC suite already passing before any code edits.
- Files changed: src/owlbear/bootstrap/hooks.py
- Tests: 16 passed in tests/test_957_notify_escalate_executors.py from scoped pytest run.
- Coverage: src/owlbear/bootstrap/hooks.py at 94 percent in scoped coverage run.
- Lint: ruff check passed on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py.
- Evidence: scoped pytest exit code 0; scoped coverage exit code 0; ruff reported All checks passed.
- Fixes applied: No behavioral fix required in this cycle. Committed pending task-scoped formatting delta in hooks.py.
- Commit: 82c3645

[[2026-03-25]] Wed 15:15

## Review Evidence

### Review: #987 - Test: HookReaction notify and escalate executor wiring

### Test Results

- pytest: 16 passed, 0 failed on tests/test_957_notify_escalate_executors.py.
- Related regression slice: 37 passed, 0 failed on tests/test_955_hook_reaction_schema_bootstrap.py.
- Evidence: both isolated pytest runs exited cleanly.

### Lint Results

- ruff: clean on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py.

### Coverage

- src/owlbear/bootstrap/hooks.py: 94 percent in the scoped coverage run.
- Note: bare coverage reports a whole-repo table; this review uses only the hooks.py row.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | TestFromAC_987_NotifyExecutorFactory::test_first_success_stops_chain, test_all_backends_tried_when_all_fail, test_backend_call_order_preserved | Yes. tests/test_957_notify_escalate_executors.py lines 62, 74, and 85 check short-circuit, all-fail traversal, and declared order against src/owlbear/bootstrap/hooks.py line 37. | COVERED |
| AC2 | TestFromAC_987_EscalateExecutorFactory::test_send_called_exactly_once, test_message_contains_event_name, test_message_contains_payload_summary | Yes. tests/test_957_notify_escalate_executors.py lines 156, 167, and 180 validate the send contract implemented at src/owlbear/bootstrap/hooks.py lines 62 and 68. | COVERED |
| AC3 | TestFromAC_987_BuildHooksNoneChannelEscalate::test_warning_logged_when_channel_none_escalate_configured, test_noop_escalate_executor_wired_when_channel_none, test_no_warning_when_channel_none_but_no_escalate_action | Yes. tests/test_957_notify_escalate_executors.py lines 215, 227, and 249 cover the warning path and negative notify-only path for src/owlbear/bootstrap/hooks.py lines 119 through 126. | COVERED |
| AC4 | TestFromAC_987_NotifyExecutorFactory::test_raising_backend_continues_chain, test_exception_does_not_propagate_to_caller, test_warning_logged_on_backend_failure | No. tests/test_957_notify_escalate_executors.py line 139 only asserts that some warning exists. src/owlbear/bootstrap/hooks.py logs both a backend-failure warning at line 51 and a generic all-backends-failed warning at line 57. Removing the backend-specific warning still leaves the AC green. | LAX |
| AC5 | TestFromAC_987_EscalateExecutorFactory::test_send_exception_propagates | Yes. tests/test_957_notify_escalate_executors.py line 195 asserts propagation from src/owlbear/bootstrap/hooks.py line 68. | COVERED |
| AC6 | TestFromAC_987_BuildHooksExecutorWiring::test_notify_executor_is_real_not_noop, test_escalate_executor_is_real_with_channel | No. tests/test_957_notify_escalate_executors.py lines 294 and 311 only check that **qualname** does not contain _noop. The captured callables from src/owlbear/bootstrap/hooks.py lines 114 through 133 are never executed, so a differently named placeholder would still pass. | LAX |
| AC7 | TestFromAC_987_BuildHooksExecutorWiring::test_retry_executor_remains_noop | Yes. tests/test_957_notify_escalate_executors.py lines 317 and 329 verify the retry slot from src/owlbear/bootstrap/hooks.py lines 114 through 116 remains the noop placeholder. | COVERED |
| AC8 | tests/test_957_notify_escalate_executors.py module and TestFromAC classes | Yes. The task file is tests/test_957_notify_escalate_executors.py line 1, and every class at lines 54, 147, 210, and 278 uses the TestFromAC_ prefix. git diff 46febf4..HEAD shows only a whitespace-only reflow in the test file, so the AC-derived tests were preserved. | COVERED |
| AC9 | task-scoped ruff run | Yes. ruff returned All checks passed on the task files. | COVERED |

#### Security Review

- No security issues found. The task stays within hook assembly and test code and adds no new shell, SQL, filesystem, or credential surface.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All TestFromAC methods in tests/test_957_notify_escalate_executors.py from commit 46febf4 | git diff 46febf4..HEAD shows only a whitespace-only list-comprehension reflow near line 263. No method names, assertions, error types, or boundary values changed. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | tests/test_957_notify_escalate_executors.py line 139 accepts any warning, and lines 294 and 311 rely on **qualname** string checks instead of behavior. |
| Negative and error paths | STRONG | lines 108, 119, 195, 215, and 249 cover raising backend, non-propagating notify failures, propagate channel.send failure, missing-channel warning, and notify-only no-warning behavior. |
| Mutation reasoning | WEAK | Deleting src/owlbear/bootstrap/hooks.py line 51 still leaves line 57 and test line 139 green. Replacing the build_hooks-wired notify or escalate callable with a differently named placeholder still leaves lines 294 and 311 green. |
| Test independence | STRONG | Each test creates fresh mocks or settings and uses local patch scopes at lines 222, 237, 260, 289, 306, and 324. |
| Descriptive names | STRONG | The test names describe the scenario and expected outcome directly, for example test_send_exception_propagates and test_no_warning_when_channel_none_but_no_escalate_action. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No test executes the callables captured from build_hooks at src/owlbear/bootstrap/hooks.py lines 114 through 133, so the assembly layer is not proven to wire behaviorally correct notify and escalate executors.
- No test distinguishes the backend-failure warning at src/owlbear/bootstrap/hooks.py line 51 from the generic all-backends-failed warning at line 57.

### Pass 2 - INFORMATIONAL

- No informational findings beyond the blocking test-strength gaps.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | src/owlbear/bootstrap/hooks.py line 37 and tests/test_957_notify_escalate_executors.py lines 62, 74, and 85 | NotifyExecutorFactory short-circuit and order tests | PASS |
| AC2 | src/owlbear/bootstrap/hooks.py lines 62 and 68 and tests/test_957_notify_escalate_executors.py lines 156, 167, and 180 | EscalateExecutorFactory send and message tests | PASS |
| AC3 | src/owlbear/bootstrap/hooks.py lines 119 through 126 and tests/test_957_notify_escalate_executors.py lines 215, 227, and 249 | BuildHooksNoneChannelEscalate warning and negative tests | PASS |
| AC4 | src/owlbear/bootstrap/hooks.py lines 51 and 57 and tests/test_957_notify_escalate_executors.py lines 108, 119, 128, and 139 | NotifyExecutorFactory failure-isolation tests | FAIL |
| AC5 | src/owlbear/bootstrap/hooks.py line 68 and tests/test_957_notify_escalate_executors.py line 195 | EscalateExecutorFactory propagation test | PASS |
| AC6 | src/owlbear/bootstrap/hooks.py lines 114 through 133 and tests/test_957_notify_escalate_executors.py lines 283, 294, 299, and 311 | BuildHooksExecutorWiring callable-name tests | FAIL |
| AC7 | src/owlbear/bootstrap/hooks.py lines 114 through 116 and tests/test_957_notify_escalate_executors.py lines 317 and 329 | Retry noop wiring test | PASS |
| AC8 | tests/test_957_notify_escalate_executors.py lines 1, 54, 147, 210, and 278 and git diff 46febf4..HEAD | File path, class prefix, and preserved TestFromAC suite | PASS |
| AC9 | task-scoped ruff output | ruff check on the task files | PASS |

### Verdict: FAIL

- Confidence .85. The implementation is green, but AC4 and AC6 are still enforced by lax tests, which leaves the TDD contract too weak for review.

### Action Taken

- Appended review evidence to task #987.
- Returning task #987 to todo for tighter AC4 and AC6 assertions.

[[2026-03-25]] Wed 15:56

## Test-Writer Notes (retry-3)

- Retry reason: reviewer FAIL (retry-2) cited AC4 and AC6 assertions too permissive.
- AC4 gap: test_warning_logged_on_backend_failure only checked some warning exists. Added test_backend_exception_warning_names_failing_backend to verify backend name appears in warning.
- AC6 gap: wiring tests only checked **qualname** strings. Added test_wired_notify_executor_invokes_backend (patches ConsoleBellBackend, calls executor, asserts mock.notify called) and test_wired_escalate_executor_calls_channel (calls executor, asserts channel.send called).
- Status: green-on-arrival. Implementation already correct; all 19 tests PASS. No fabricated failures per policy.
- Preserved: 16 prior tests. Added: 3 behavioral tests for AC4 and AC6.
- Commit: 8c00f1a
- ruff: clean

[[2026-03-25]] Wed 16:06

## Builder Notes

- Build mode: Green on arrival in this retry cycle.
- Files changed: None.
- Tests: 19 passed in tests/test_957_notify_escalate_executors.py using explicit pytest_asyncio plugin loading.
- Coverage: src/owlbear/bootstrap/hooks.py reported 94 percent in the scoped coverage run.
- Lint: ruff check passed on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py.
- Evidence: initial run without async plugin support failed at collection for async tests; corrected scoped pytest run passed with 19 tests, scoped coverage run passed, and task scoped git status is clean.
- Fixes applied: None required because AC tests are already green in current source.
- Commit: None, no task file diffs in this cycle.

[[2026-03-25]] Wed 16:27

## Review Evidence

### Review: #987 - Test: HookReaction notify and escalate executor wiring

### Test Results

- pytest: 19 passed, 0 failed on tests/test_957_notify_escalate_executors.py in 2.46s.
- Related regression slice: 37 passed, 0 failed on tests/test_955_hook_reaction_schema_bootstrap.py in 2.50s.

### Lint Results

- ruff: clean on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py.

### Coverage

- src/owlbear/bootstrap/hooks.py: 94 percent in the isolated scoped coverage run.
- Note: bare coverage reports whole-repo rows; this verdict uses only the hooks.py row.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | TestFromAC_987_NotifyExecutorFactory::test_first_success_stops_chain; test_all_backends_tried_when_all_fail; test_backend_call_order_preserved | Yes. tests/test_957_notify_escalate_executors.py lines 62, 74, and 85 catch short-circuit, all-fail traversal, and declared order for src/owlbear/bootstrap/hooks.py lines 37 and 47. | COVERED |
| AC2 | TestFromAC_987_EscalateExecutorFactory::test_send_called_exactly_once; test_message_contains_event_name; test_message_contains_payload_summary | Yes. tests/test_957_notify_escalate_executors.py lines 184, 195, and 208 verify single send, event-name inclusion, and payload summary for src/owlbear/bootstrap/hooks.py lines 62, 67, and 68. | COVERED |
| AC3 | TestFromAC_987_BuildHooksNoneChannelEscalate::test_warning_logged_when_channel_none_escalate_configured; test_noop_escalate_executor_wired_when_channel_none; test_no_warning_when_channel_none_but_no_escalate_action | Yes. tests/test_957_notify_escalate_executors.py lines 243, 255, and 277 verify warning emission, noop fallback wiring, and the notify-only negative path for src/owlbear/bootstrap/hooks.py lines 114, 119, 124, and 126. | COVERED |
| AC4 | TestFromAC_987_NotifyExecutorFactory::test_raising_backend_continues_chain; test_exception_does_not_propagate_to_caller; test_warning_logged_on_backend_failure; test_backend_exception_warning_names_failing_backend | Yes. tests/test_957_notify_escalate_executors.py lines 108, 119, 128, 139, 142, 158, and 164 verify continuation, no propagation, warning emission, and backend-name specificity for src/owlbear/bootstrap/hooks.py lines 47, 51, and 57. | COVERED |
| AC5 | TestFromAC_987_EscalateExecutorFactory::test_send_exception_propagates | Yes. tests/test_957_notify_escalate_executors.py lines 223 and 229 assert propagation from src/owlbear/bootstrap/hooks.py line 68. | COVERED |
| AC6 | TestFromAC_987_BuildHooksExecutorWiring::test_notify_executor_is_real_not_noop; test_escalate_executor_is_real_with_channel; test_wired_notify_executor_invokes_backend; test_wired_escalate_executor_calls_channel | Yes. tests/test_957_notify_escalate_executors.py lines 311, 327, 364, 381, 384, and 397 verify the wired callables are not noop placeholders and actually invoke a backend and channel send for src/owlbear/bootstrap/hooks.py lines 114, 123, and 133. | COVERED |
| AC7 | TestFromAC_987_BuildHooksExecutorWiring::test_retry_executor_remains_noop | Yes. tests/test_957_notify_escalate_executors.py lines 345, 355, and 357 verify the retry slot remains the internal noop placeholder from src/owlbear/bootstrap/hooks.py line 114. | COVERED |
| AC8 | tests/test_957_notify_escalate_executors.py module and TestFromAC classes | Yes. the task file is tests/test_957_notify_escalate_executors.py, classes at lines 54, 175, 238, and 306 use the TestFromAC_ prefix, imports at lines 18 through 20 require the executor factories, and git grep against c7401c3^ for those symbols in src/owlbear/bootstrap/hooks.py returned exit code 1, so the suite is RED against pre-implementation code. | COVERED |
| AC9 | task-scoped ruff run | Yes. ruff returned All checks passed on the task files. | COVERED |

#### Security Review

- No security issues found. The task stays within hook assembly and test code and adds no shell, SQL, filesystem, credential, or unsafe deserialization surface.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suite present in commit 46febf4 | Builder commits a0e0358 and 82c3645 did not weaken or remove any existing TestFromAC method. The later test-writer commit 8c00f1a only added stricter AC4 and AC6 coverage plus a whitespace-only reflow. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | tests/test_957_notify_escalate_executors.py lines 158 and 164 require the backend-failure warning to name the failing backend, and lines 381 and 397 execute the build_hooks-wired callables rather than only checking names. |
| Negative and error paths | STRONG | lines 108, 119, 223, 243, and 277 cover raising backend continuation, swallowed notify failure, propagated channel failure, missing-channel warning, and notify-only no-warning behavior. |
| Mutation reasoning | STRONG | Removing src/owlbear/bootstrap/hooks.py line 51 breaks lines 158 and 164; replacing the wired notify or escalate callable with a noop-equivalent breaks lines 381 or 397. |
| Test independence | STRONG | Each test builds fresh mocks or settings and uses local patch scopes; no shared mutable fixture state is required. |
| Descriptive names | STRONG | Method names such as test_backend_exception_warning_names_failing_backend and test_wired_escalate_executor_calls_channel state the scenario and expected outcome clearly. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested paths remain in the task implementation. src/owlbear/bootstrap/hooks.py lines 37 through 57, 62 through 68, and 114 through 133 are exercised across success, failure, warning, no-channel, and wired-behavior paths.

### Pass 2 - INFORMATIONAL

- src/owlbear/bootstrap/hooks.py lines 86 and 88 still describe reaction_executors as a noop dict later replaced with real executors. Current behavior wires a real notify executor and conditionally a real escalate executor inside build_hooks itself. This is documentation drift, not a blocker.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | src/owlbear/bootstrap/hooks.py lines 37 and 47; tests/test_957_notify_escalate_executors.py lines 62, 74, and 85 | test_first_success_stops_chain; test_all_backends_tried_when_all_fail; test_backend_call_order_preserved | PASS |
| AC2 | src/owlbear/bootstrap/hooks.py lines 62, 67, and 68; tests/test_957_notify_escalate_executors.py lines 184, 195, and 208 | test_send_called_exactly_once; test_message_contains_event_name; test_message_contains_payload_summary | PASS |
| AC3 | src/owlbear/bootstrap/hooks.py lines 114, 119, 124, and 126; tests/test_957_notify_escalate_executors.py lines 243, 255, and 277 | test_warning_logged_when_channel_none_escalate_configured; test_noop_escalate_executor_wired_when_channel_none; test_no_warning_when_channel_none_but_no_escalate_action | PASS |
| AC4 | src/owlbear/bootstrap/hooks.py lines 47, 51, and 57; tests/test_957_notify_escalate_executors.py lines 108, 119, 128, 139, 142, 158, and 164 | test_raising_backend_continues_chain; test_exception_does_not_propagate_to_caller; test_warning_logged_on_backend_failure; test_backend_exception_warning_names_failing_backend | PASS |
| AC5 | src/owlbear/bootstrap/hooks.py line 68; tests/test_957_notify_escalate_executors.py lines 223 and 229 | test_send_exception_propagates | PASS |
| AC6 | src/owlbear/bootstrap/hooks.py lines 114, 123, and 133; tests/test_957_notify_escalate_executors.py lines 311, 327, 364, 381, 384, and 397 | test_notify_executor_is_real_not_noop; test_escalate_executor_is_real_with_channel; test_wired_notify_executor_invokes_backend; test_wired_escalate_executor_calls_channel | PASS |
| AC7 | src/owlbear/bootstrap/hooks.py line 114; tests/test_957_notify_escalate_executors.py lines 345, 355, and 357 | test_retry_executor_remains_noop | PASS |
| AC8 | tests/test_957_notify_escalate_executors.py lines 18 through 20, 54, 175, 238, and 306; git grep on c7401c3^ returned exit code 1 for both executor factory names in src/owlbear/bootstrap/hooks.py | module import contract and TestFromAC class structure | PASS |
| AC9 | task-scoped ruff output | ruff check on src/owlbear/bootstrap/hooks.py and tests/test_957_notify_escalate_executors.py | PASS |

### Verdict: PASS

- Confidence .95. The earlier AC4 and AC6 laxity is closed by the strengthened tests, and the current implementation satisfies the stronger suite.

### Action Taken

- Appended review evidence to task #987.
- Next status is docs.

[[2026-03-25]] Wed 17:08

## Audit

### AC Verification

AC1 PASS: _make_notify_executor at hooks.py L37 iterates backends, short-circuits on first True. Tests L62, L74, L85 verify.
AC2 PASS: _make_escalate_executor at hooks.py L62 calls channel.send with formatted message. Tests L184, L195, L208 verify.
AC3 PASS: hooks.py L119-L126 guards escalation warning to escalate-configured case. Tests L243, L255, L277 verify including negative path.
AC4 PASS: hooks.py L49-L57 catches backend exceptions, logs warning with backend name. Tests L108, L119, L128, L142, L158, L164 verify including backend-name specificity.
AC5 PASS: hooks.py L68 propagates channel.send exceptions. Test L223 verifies.
AC6 PASS: hooks.py L114-L133 wires real executors. Tests L311, L327, L364, L381, L397 verify including behavioral invocation of wired callables.
AC7 PASS: hooks.py L114 keeps retry as noop. Tests L345, L355 verify.
AC8 PASS: File at tests/test_957_notify_escalate_executors.py, all 4 classes use TestFromAC_ prefix.
AC9 PASS: ruff clean on both task files.

### Test Results

- Task-scoped pytest: 19 passed (test_957) + 37 passed (test_955 regression) in 2.59s
- Full suite: 4405 passed, 80 failed (pre-existing RED-phase), 2 skipped. No task-related failures.
- ruff: All checks passed on hooks.py and test_957_notify_escalate_executors.py

### Commit Chain

c7401c3 feat: wire hook reaction notify and escalate executors (#987, builder)
46febf4 test: add failing negative test for notify-only no-channel case (#987, test-writer)
a0e0358 fix: scope escalate warning to configured escalate action (#987, builder)
82c3645 chore: normalize hook executor wiring formatting (#987, builder)
8c00f1a test: strengthen AC4/AC6 assertions for notify/escalate wiring (#987, test-writer)
6bd2349 docs: fix stale build_hooks docstring and copilot-instructions (#987, writer)

### Architect Quality: 4/5

AC was specific and led to solid implementation. Minor gap: notify-only no-warning negative path was discovered by reviewer, not in original AC, but AC3 implied it.

### Confidence: .96

### Action: archive

[[2026-03-25]] Wed 17:09

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1430f65 | chore | kanban/tasks/987-*.md | #987 |
