---
id: 515
title: Implement circuit breaker for Copilot API
status: done
priority: important
created: 2026-03-04T07:38:26.1410302+01:00
updated: 2026-03-08T04:11:32.2441488+01:00
started: 2026-03-06T23:49:41.1231488+01:00
completed: 2026-03-08T04:11:32.2441488+01:00
tags:
    - audit
    - resilience
    - scope:core
depends_on:
    - 512
class: standard
---

CB-1 from docs/resilience-audit.md: No circuit breakers anywhere. If Copilot API returns 503 for 10 minutes, every turn burns retries with backoff. No fast-fail mechanism.

See docs/circuit-breaker-research.md for full analysis.

## Architecture Decision

Option B (manual ~60 LOC class) + placement P1 (httpx transport wrapper):

- core/circuit_breaker.py: CircuitBreaker class (closed/open/half_open states)
- core/circuit_breaker.py: CircuitBreakerTransport(httpx.AsyncBaseTransport)
- providers/copilot.py: wrap AsyncTenacityTransport in CircuitBreakerTransport
- core/errors.py: add CircuitOpenError, classify as PERMANENT

depends_on: [512]

## Acceptance Criteria

- [ ] CircuitBreaker class in core/circuit_breaker.py with 3 states: closed, open, half_open
- [ ] Configurable fail_max (default 5) and reset_timeout (default 60s)
- [ ] State transitions: closed->open after fail_max consecutive transient failures; open->half_open after reset_timeout; half_open->closed on success; half_open->open on failure
- [ ] asyncio.Lock guards state transitions (async-safe)
- [ ] CircuitOpenError exception class in core/circuit_breaker.py
- [ ] CircuitOpenError classified as PERMANENT in core/errors.py classify_error()
- [ ] CircuitBreakerTransport(httpx.AsyncBaseTransport) wraps inner transport; raises CircuitOpenError when open; calls on_success/on_failure based on response
- [ ] Only transient errors (via classify_error) count as failures -- auth/permanent errors do not trip the breaker
- [ ] providers/copilot.py: AsyncTenacityTransport wrapped in CircuitBreakerTransport
- [ ] Module-level or settings-injected breaker instance so state persists across client recreations (e.g. auth refresh)
- [ ] ruff clean, all existing tests pass
