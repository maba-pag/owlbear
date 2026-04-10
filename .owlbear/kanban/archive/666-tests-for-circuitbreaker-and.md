---
id: 666
title: Tests for CircuitBreaker and CircuitBreakerTransport (#515)
status: archived
priority: important
created: 2026-03-08T02:11:08.2582735+01:00
updated: 2026-03-09T19:39:36.8619686+01:00
started: 2026-03-08T03:32:09.2694996+01:00
completed: 2026-03-09T19:39:36.8619686+01:00
tags:
    - test
    - resilience
    - scope:core
class: standard
---

Test companion for #515. Verify circuit breaker state machine and transport integration.

depends_on: [515]

## Acceptance Criteria

- [ ] Test: closed state allows calls through
- [ ] Test: closed->open after fail_max (5) consecutive transient failures
- [ ] Test: open state raises CircuitOpenError immediately (no HTTP call made)
- [ ] Test: open->half_open after reset_timeout (60s) elapsed
- [ ] Test: half_open->closed on successful call
- [ ] Test: half_open->open on failed call (single failure resets)
- [ ] Test: non-transient errors (auth, permanent) do NOT increment failure counter
- [ ] Test: CircuitBreakerTransport delegates to inner transport when closed
- [ ] Test: CircuitBreakerTransport raises CircuitOpenError when open
- [ ] Test: classify_error(CircuitOpenError()) returns PERMANENT
- [ ] Tests in tests/test_circuit_breaker.py
- [ ] ruff clean, all tests pass

[[2026-03-09]] Mon 19:39
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| closed state allows calls through | TestCircuitBreakerInitialState::test_closed_state_allows_calls PASSED | PASS |
| closed->open after fail_max (5) consecutive transient failures | TestClosedToOpen::test_failures_at_threshold_open_circuit PASSED | PASS |
| open state raises CircuitOpenError immediately (no HTTP call) | TestOpenState + TransportOpen: inner.assert_not_called() PASSED | PASS |
| open->half_open after reset_timeout elapsed | TestOpenToHalfOpen::test_transitions_to_half_open_after_timeout PASSED | PASS |
| half_open->closed on successful call | TestHalfOpenTransitions::test_half_open_success_closes_circuit PASSED | PASS |
| half_open->open on failed call (single failure resets) | TestHalfOpenTransitions::test_half_open_failure_reopens_circuit PASSED | PASS |
| non-transient errors do NOT increment failure counter | TestNonTransientErrors: auth(401) + permanent(400) x3 each, state=closed PASSED | PASS |
| Transport delegates to inner when closed | TestCircuitBreakerTransportClosed::test_delegates_to_inner_transport PASSED | PASS |
| Transport raises CircuitOpenError when open | TestCircuitBreakerTransportOpen::test_raises_circuit_open_error_when_open PASSED | PASS |
| classify_error(CircuitOpenError()) returns PERMANENT | TestClassifyCircuitOpenError::test_circuit_open_error_is_permanent PASSED | PASS |
| Tests in tests/test_circuit_breaker.py | File exists, 16 tests collected and run | PASS |
| ruff clean, all tests pass | ruff check: All checks passed; pytest: 16/16 passed | PASS |

### Test Results
- pytest (scoped): 16 passed, 0 failed in 1.27s
- pytest (full): 1315 passed, 2 failed (pre-existing env issues: slack_sdk missing, Windows tmpdir permission), 20 skipped  no regressions from #666
- ruff: All checks passed

### Confidence: 1.0
### Action: archive
