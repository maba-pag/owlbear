---
id: 666
title: Tests for CircuitBreaker and CircuitBreakerTransport (#515)
status: done
priority: important
created: 2026-03-08T02:11:08.2582735+01:00
updated: 2026-03-08T03:32:09.2694996+01:00
started: 2026-03-08T03:32:09.2694996+01:00
completed: 2026-03-08T03:32:09.2694996+01:00
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
