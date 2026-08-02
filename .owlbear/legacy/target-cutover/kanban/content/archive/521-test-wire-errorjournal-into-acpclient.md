---
id: 521
title: 'Test: Wire ErrorJournal into AcpClient'
status: archived
priority: medium
created: 2026-04-01 15:14:45.431847+02:00
updated: 2026-04-10 02:02:10.434689+02:00
started: 2026-04-02 01:03:55.809090+02:00
completed: 2026-04-10 02:02:10.434689+02:00
tags:
- phase-2
- scope:orchestrator
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
RED phase tests for _ErrorLogger Protocol wiring in AcpClient (#148).

## AC
- [ ] Tests in tests/test_acp_client.py in a TestFromAC_ErrorLoggerWiring class
- [ ] Test: log_error called with correct category, method, message when initialize raises RequestError
- [ ] Test: log_error called with category=transient, method=initialize when initialize raises BrokenPipeError
- [ ] Test: log_error called with correct args when new_session raises RequestError
- [ ] Test: log_error called with category=transient, method=new_session when new_session raises ConnectionError
- [ ] Test: log_error called with correct args when prompt raises RequestError
- [ ] Test: log_error called with category=transient, method=prompt when prompt raises BrokenPipeError
- [ ] Test: log_error NOT called when error_logger is None (default behavior)
- [ ] Test: TimeoutError in prompt() does NOT call log_error (excluded by design)
- [ ] All tests use MagicMock satisfying _ErrorLogger Protocol
- [ ] All new tests FAIL (RED phase)
- [ ] ruff clean

[[2026-04-01]] Wed 18:01
## Test-Writer Notes
- Test file: tests/test_acp_client.py
- Classes: TestFromAC_ErrorLoggerWiring
- Tests per category: happy 0, edge 1, error 6, boundary 1
- Total: 8 tests, all FAIL (TypeError: unexpected keyword argument 'error_logger') OK
- ruff: clean
- AC coverage:
  initialize+RequestError: test_initialize_request_error_calls_log_error_with_category_method_message
  initialize+BrokenPipeError: test_initialize_broken_pipe_calls_log_error_category_transient
  new_session+RequestError: test_new_session_request_error_calls_log_error_with_correct_args
  new_session+ConnectionError: test_new_session_connection_error_calls_log_error_category_transient
  prompt+RequestError: test_prompt_request_error_calls_log_error_with_correct_args
  prompt+BrokenPipeError: test_prompt_broken_pipe_calls_log_error_category_transient
  error_logger=None default: test_no_log_error_when_error_logger_is_none
  TimeoutError excluded: test_timeout_error_in_prompt_does_not_call_log_error

[[2026-04-01]] Wed 22:54
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear_orchestrator/acp_client.py
- Tests: 42 passed (8 new TestFromAC_ErrorLoggerWiring + 34 pre-existing), 0 failures
- Coverage: 99% on acp_client.py (line 98 is Protocol stub ellipsis, unreachable by design)
- Lint: ruff clean
- Evidence: 42 passed, 6 warnings in 0.55s
- Changes: added _ErrorLogger Protocol; error_logger kwarg in __init__; log_error calls in initialize/new_session/prompt for RequestError and BrokenPipeError/ConnectionError; TimeoutError path unchanged (no log_error call)

[[2026-04-01]] Wed 23:28
## Review Evidence

### Test Results
- pytest tests/test_acp_client.py: 42 passed, 0 failed, 6 warnings (pre-existing RuntimeWarning about unawaited coroutine in asyncio.wait_for mock - not new)

### Lint Results
- ruff check packages/orchestrator/src/ tests/test_acp_client.py: All checks passed!

### Coverage
- packages/orchestrator/src/owlbear_orchestrator/acp_client.py: 99% (line 98 = Protocol stub ellipsis, unreachable by design)

### Security (6.1)
- No hardcoded secrets, no injection, no path traversal, no insecure deserialization
- No new dependencies
- CLEAN

### Test-Writer Coverage Audit (6.0)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| init+RequestError log_error | test_initialize_request_error_calls_log_error_with_category_method_message | Yes - asserts category, method, message | COVERED |
| init+BrokenPipeError category=transient | test_initialize_broken_pipe_calls_log_error_category_transient | Yes - asserts TRANSIENT, method | COVERED |
| new_session+RequestError log_error | test_new_session_request_error_calls_log_error_with_correct_args | Yes - asserts category, method, message | COVERED |
| new_session+ConnectionError category=transient | test_new_session_connection_error_calls_log_error_category_transient | Yes - asserts TRANSIENT, method | COVERED |
| prompt+RequestError log_error | test_prompt_request_error_calls_log_error_with_correct_args | Yes - asserts category, method, message | COVERED |
| prompt+BrokenPipeError category=transient | test_prompt_broken_pipe_calls_log_error_category_transient | Yes - asserts TRANSIENT, method | COVERED |
| logger=None no crash | test_no_log_error_when_error_logger_is_none | Yes - AttributeError would escape pytest.raises(AcpClientError) | COVERED |
| TimeoutError not logged | test_timeout_error_in_prompt_does_not_call_log_error | Yes - assert_not_called() | COVERED |

### TestFromAC Comparison (6.2)
Builder Notes: only acp_client.py changed - test file untouched. All 8 TestFromAC_ErrorLoggerWiring methods PRESERVED.

### Test Quality (6.3)
- Assertion specificity: STRONG - tests check exact ErrorCategory enum values, exact method strings, message substrings
- Negative/error-path: STRONG - 6 error-path tests + 1 none-guard + 1 timeout-excluded
- Test independence: STRONG - each test creates own conn/error_logger mocks
- Test names: STRONG - descriptive, scenario+expected-outcome pattern

### Implementation-Aware Gap Analysis (6.5)
acp_client.py: _ErrorLogger Protocol (line ~43), error_logger kwarg in __init__, guarded log_error calls in initialize/new_session/prompt for RequestError and BrokenPipeError/ConnectionError. TimeoutError handler has no log_error call.
All non-trivial branches have test coverage. No significant untested paths identified.

### Builder Process Quality (6.7)
Single Builder Notes section - no retries. CLEAN.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_ErrorLoggerWiring class in test_acp_client.py | test_acp_client.py line 505 | PASS |
| init+RequestError calls log_error w/ category/method/message | test_initialize_request_error_calls_log_error... L511 - asserts PERMANENT, initialize, Parse error | PASS |
| init+BrokenPipeError calls log_error category=transient | test_initialize_broken_pipe... L525 - asserts TRANSIENT, initialize | PASS |
| new_session+RequestError calls log_error correct args | test_new_session_request_error... L538 - asserts TRANSIENT, new_session, Internal error | PASS |
| new_session+ConnectionError calls log_error category=transient | test_new_session_connection_error... L553 - asserts TRANSIENT, new_session | PASS |
| prompt+RequestError calls log_error correct args | test_prompt_request_error... L566 - asserts PERMANENT, prompt, Method not found | PASS |
| prompt+BrokenPipeError calls log_error category=transient | test_prompt_broken_pipe... L580 - asserts TRANSIENT, prompt | PASS |
| log_error NOT called when error_logger is None | test_no_log_error_when_error_logger_is_none L592 - None passthrough, AcpClientError raised | PASS |
| TimeoutError in prompt does NOT call log_error | test_timeout_error_in_prompt_does_not_call_log_error L604 - assert_not_called() | PASS |
| All tests use MagicMock satisfying _ErrorLogger Protocol | MagicMock() used in all 8 parametrized cases | PASS |
| All new tests FAIL (RED phase) | Test-writer notes: TypeError on unexpected kwarg 'error_logger' - confirmed | PASS |
| ruff clean | ruff check: All checks passed! | PASS |

### Verdict: PASS
Confidence: .93

[[2026-04-01]] Wed 23:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | AcpClient not referenced; kwarg is internal implementation |
| 2 | Docstrings | Yes | Updated | Added error_logger arg to AcpClient class docstring Args section |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase |

### Files Updated
- packages/orchestrator/src/owlbear_orchestrator/acp_client.py (docstring only)

### Scratch Files Cleaned
- None

[[2026-04-02]] Thu 01:03
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_ErrorLoggerWiring class | test_acp_client.py L505 | PASS |
| init+RequestError log_error | test L511 asserts PERMANENT, initialize, Parse error | PASS |
| init+BrokenPipeError category=transient | test L525 asserts TRANSIENT, initialize | PASS |
| new_session+RequestError log_error | test L538 asserts TRANSIENT, new_session, Internal error | PASS |
| new_session+ConnectionError category=transient | test L553 asserts TRANSIENT, new_session | PASS |
| prompt+RequestError log_error | test L566 asserts PERMANENT, prompt, Method not found | PASS |
| prompt+BrokenPipeError category=transient | test L580 asserts TRANSIENT, prompt | PASS |
| logger=None no crash | test L592 None passthrough, no AttributeError | PASS |
| TimeoutError excluded | test L620 assert_not_called() | PASS |
| All use MagicMock | MagicMock() in all 8 tests confirmed | PASS |
| All new tests FAIL (RED) | Test-writer notes: TypeError confirmed | PASS |
| ruff clean | ruff check: All checks passed! | PASS |

### Test Results
- pytest test_acp_client.py: 42 passed, 0 failed, 6 warnings
- Full suite (excl test_tools_exclude_493.py): 2236 passed, 249 failed (pre-existing, none in task scope)
- ruff: All checks passed!

### Upstream Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3027bf3 | test | tests/test_acp_client.py | #521 |
| 8587257 | feat | acp_client.py | #521 |
| f915fb1 | docs | acp_client.py (docstring) | #521 |

### AC Quality Score: 4/5
AC was specific and complete. All 12 lines mapped 1:1 to tests with no builder improvisation needed.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

[[2026-04-10]] Fri 02:02
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_ErrorLoggerWiring class | test_acp_client.py L505 (read verified) | PASS |
| init+RequestError log_error | test L511 asserts PERMANENT, initialize, "Parse error" | PASS |
| init+BrokenPipeError category=transient | test L525 asserts TRANSIENT, initialize | PASS |
| new_session+RequestError log_error | test L538 asserts TRANSIENT, new_session, "Internal error" | PASS |
| new_session+ConnectionError category=transient | test L553 asserts TRANSIENT, new_session | PASS |
| prompt+RequestError log_error | test L566 asserts PERMANENT, prompt, "Method not found" | PASS |
| prompt+BrokenPipeError category=transient | test L580 asserts TRANSIENT, prompt | PASS |
| logger=None no crash | test L592 None passthrough, no AttributeError | PASS |
| TimeoutError excluded | test L620 assert_not_called(); impl confirmed no log_error in TimeoutError handler | PASS |
| All use MagicMock | MagicMock() in all 8 tests confirmed via code read | PASS |
| All new tests FAIL (RED) | Test-writer notes: TypeError confirmed | PASS |
| ruff clean | ruff check: All checks passed! | PASS |

### Test Results
- pytest test_acp_client.py: 42 passed, 0 failed, 6 warnings
- Full suite: 3054 passed, 277 failed, 18 skipped, 2 errors — none in task scope
- ruff: All checks passed!

### Upstream Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3027bf3 | test | tests/test_acp_client.py | #521 |
| 8587257 | feat | acp_client.py | #521 |
| f915fb1 | docs | acp_client.py (docstring) | #521 |

### Architect Quality: 4/5
12 AC lines, all specific and testable. 1:1 mapping to tests with no builder improvisation. Minor: title says "ErrorJournal" but AC body correctly specifies "_ErrorLogger Protocol" throughout.

### Deduction Breakdown
- AC lines without evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality ≤ 3: no (-.00)
- Missing reviewer evidence: no (-.00)
- Full-suite failures in task scope: none (-.00)

### Confidence: 1.0
### Action: archive
