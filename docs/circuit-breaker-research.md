# Circuit Breaker for Copilot API

> **Owning task:** #515 — Implement circuit breaker for Copilot API
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

OwlBear's Copilot API integration has two retry layers (HTTP transport in `providers/copilot.py` L57-69, tool-level in `tools/hooked.py` L127-134), but **no fast-fail mechanism**. If the Copilot API returns 503 for 10 minutes, every agent turn burns 3 retries × backoff before failing. The daemon's `_recover_from_error` adds another 3 retries on top (R-3 in `docs/resilience-audit.md`), totalling up to 9 attempts per turn — all wasted against a down service.

**Question:** What is the simplest, KISS-aligned circuit breaker that prevents cascading delays without adding unnecessary dependencies?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | pybreaker (v1.4.1) | <https://github.com/danielfm/pybreaker> | .85 — mature, 656 stars, BSD-3, thread-safe, exclude-list, listeners, success_threshold |
| 2 | aiobreaker | <https://github.com/arlyon/aiobreaker> | .40 — asyncio fork of pybreaker, 27 stars, unmaintained (last commit 5y ago) |
| 3 | tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | .70 — custom stop/retry callbacks can model CB state; already a dependency |
| 4 | Circuit Breaker pattern (Nygard / microservices.io) | <https://microservices.io/patterns/reliability/circuit-breaker.html> | .90 — canonical pattern definition: closed → open → half-open |
| 5 | OwlBear resilience audit | `docs/resilience-audit.md` CB-1, R-3 | 1.0 — identifies the gap and existing retry topology |

## 3. Analysis

### 3.1 Option Comparison

| Criterion | A: pybreaker (.80) | B: Manual class (~60 LOC) (.85) | C: Tenacity custom stop (.55) |
|-----------|--------------------|---------------------------------|-------------------------------|
| New dependency | Yes (pybreaker) | No | No (tenacity exists) |
| Async-native | No (sync + threading locks) | Yes (asyncio.Lock) | Partial (async retry, sync state) |
| State machine | Full (closed/open/half-open + listeners) | Full (closed/open/half-open) | Bolted-on (state in closure) |
| Exclude list | Built-in (exclude kwarg + callables) | Manual (reuse `classify_error`) | Manual |
| Integration with existing retry | Separate layer (wraps or sits alongside tenacity) | Checks before retry; raises `CircuitOpenError` | Embedded in tenacity stop/retry |
| Testability | Mocking state_storage or direct `.open()` | Direct attribute setting | Harder — state hidden in retry internals |
| KISS score | Medium — full library for one use | High — exactly what we need, nothing more | Low — abusing tenacity's API |
| LOC estimate | ~10 (config) + 1 dep | ~60 (class) + ~20 (integration) | ~40 (callbacks) but fragile |
| Monitoring | `.fail_counter`, `.current_state`, listeners | Properties + logging | Buried in retry statistics |

### 3.2 Placement Options

The circuit breaker must sit **above** both retry layers to prevent retries from firing at all when the circuit is open:

```
agent.turn() → daemon._recover_from_error() → [CIRCUIT BREAKER] → copilot HTTP → [transport retry]
```

Concretely:

- **Option P1:** In `providers/copilot.py` as an `httpx.AsyncBaseTransport` wrapper around `AsyncTenacityTransport` — intercepts every HTTP call.
- **Option P2:** In `core/retry.py` as a shared module — wraps `TRANSIENT_RETRY` or provides a `check_circuit()` guard.
- **Option P3:** In `daemon.py` before `agent.turn()` — highest level, prevents the turn entirely.

**Recommendation: P1** (.80 confidence). Placing it at the transport layer means all Copilot HTTP calls (including those from PydanticAI internals) are protected. A `CircuitBreakerTransport` wrapping `AsyncTenacityTransport` is the cleanest integration.

### 3.3 Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| False positive (CB opens during brief hiccup) | Low — 5 consecutive failures is a solid threshold | Half-open probe after 60s allows recovery |
| CB state lost on daemon restart | Certain — in-memory state | Acceptable — daemon restart implies fresh start; no need for persistence |
| Interaction with daemon-level retry (R-3) | Medium — daemon retry would see `CircuitOpenError` | Classify `CircuitOpenError` as PERMANENT in `classify_error` so daemon doesn't retry |
| Thread safety in async context | Low — single event loop | Use `asyncio.Lock` for state transitions |

## 4. Recommendation (.85 confidence)

**Option B (manual class) + placement P1 (transport wrapper).**

Rationale:

- **KISS:** ~60 LOC, zero new dependencies. pybreaker is nice but adds a dep for a single use, and its threading model doesn't align with our async daemon.
- **YAGNI:** We need one circuit breaker for one integration point. pybreaker's Redis storage, listener system, and generator support are unused.
- **DRY:** Reuse `classify_error` to decide what counts as a failure (transient errors only).

Implementation sketch:

1. `core/circuit_breaker.py` — `CircuitBreaker` class with `closed`/`open`/`half_open` states, `fail_max=5`, `reset_timeout=60`, `asyncio.Lock`.
2. `core/circuit_breaker.py` — `CircuitBreakerTransport(httpx.AsyncBaseTransport)` wrapping inner transport; calls `breaker.before_call()` / `breaker.on_success()` / `breaker.on_failure()`.
3. `providers/copilot.py` — wrap `AsyncTenacityTransport` in `CircuitBreakerTransport`.
4. `core/errors.py` — add `CircuitOpenError` exception; classify as `PERMANENT`.
5. Tests: unit tests for state transitions, transport integration test with mocked HTTP.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement CircuitBreaker class in core/circuit_breaker.py" --status backlog --priority needed --tags "resilience,scope:core,phase-13" --body "~60 LOC async circuit breaker: 3 states (closed/open/half_open), fail_max=5, reset_timeout=60s, asyncio.Lock for state transitions. Reuse classify_error for failure detection. Add CircuitOpenError exception. AC: (1) CircuitBreaker transitions closed→open after 5 consecutive transient failures, (2) open→half_open after 60s, (3) half_open→closed on success, (4) half_open→open on failure, (5) CircuitOpenError classified as PERMANENT. See docs/circuit-breaker-research.md §4."

kanban\kanban-md.exe create "Implement CircuitBreakerTransport wrapper" --status backlog --priority needed --tags "resilience,scope:core,phase-13" --body "httpx.AsyncBaseTransport that wraps inner transport with circuit breaker guard. Calls breaker.before_call() (raises CircuitOpenError if open), delegates to inner, calls on_success/on_failure based on result. AC: (1) Transport raises CircuitOpenError when circuit is open, (2) successful responses close circuit, (3) transient failures increment failure counter. See docs/circuit-breaker-research.md §4." --depends-on "Implement CircuitBreaker class in core/circuit_breaker.py"

kanban\kanban-md.exe create "Wire CircuitBreakerTransport into Copilot provider" --status backlog --priority needed --tags "resilience,auth,phase-13" --body "In providers/copilot.py, wrap AsyncTenacityTransport in CircuitBreakerTransport. Module-level breaker instance so state persists across create_copilot_client calls. AC: (1) Copilot HTTP calls go through circuit breaker, (2) 5 consecutive 503s trips circuit, (3) daemon receives CircuitOpenError instead of burning retries. See docs/circuit-breaker-research.md §4." --depends-on "Implement CircuitBreakerTransport wrapper"
```
