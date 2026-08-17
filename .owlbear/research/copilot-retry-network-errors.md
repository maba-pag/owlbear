# Add ConnectError and TimeoutException to Copilot Transport Retry

> **Owning task:** #469 — Add ConnectError and TimeoutException to Copilot transport retry
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

`providers/copilot.py` builds an `AsyncTenacityTransport` with `retry=retry_if_exception_type(httpx.HTTPStatusError)`. This retries on HTTP 429/502/503/504 (raised by `_validate_transient_response`), but `httpx.ConnectError` and `httpx.TimeoutException` bypass retry entirely. If the Copilot API is briefly unreachable (DNS blip, TLS handshake timeout, proxy hiccup), the first request fails permanently. Should these be retried?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | httpx exception hierarchy docs | <https://www.python-httpx.org/exceptions/> | .95 — Authoritative hierarchy: `ConnectError` (under `NetworkError`) and `TimeoutException` are siblings under `TransportError`, completely separate from `HTTPStatusError` |
| 2 | tenacity API docs | <https://tenacity.readthedocs.io/en/latest/api.html> | .90 — `retry_if_exception_type` accepts a tuple of types |
| 3 | PydanticAI `retries.py` (pydantic-ai repo) | <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/retries.py> | .85 — `AsyncTenacityTransport.handle_async_request` wraps `self.wrapped.handle_async_request(req)` in the tenacity `@retry` decorator — network exceptions thrown by the inner transport are caught |
| 4 | OwlBear `core/errors.py` | Local: `src/owlbear/core/errors.py` L78-82 | .95 — `classify_error` already classifies `ConnectError`, `TimeoutException`, `ConnectionError`, `TimeoutError` as `TRANSIENT` |
| 5 | OwlBear `tools/hooked.py` L61-64 | Local: `src/owlbear/tools/hooked.py` | .90 — Tool-level retry uses `classify_error` which already covers network errors |

## 3. Analysis

### 3.1 Exception flow through AsyncTenacityTransport

```text
httpx.AsyncClient.request()
  └─ AsyncTenacityTransport.handle_async_request()    ← tenacity @retry wraps this
       └─ self.wrapped.handle_async_request(req)      ← ConnectError/TimeoutException raised HERE
       └─ self.validate_response(response)            ← HTTPStatusError raised here (429/502/503/504)
```

Network errors occur at the inner transport call, *before* `validate_response`. Tenacity's decorator catches them — but only if `retry_if_exception_type` matches. Currently it only matches `HTTPStatusError`, so network errors propagate immediately.

### 3.2 Option comparison

| Criterion | A: Add tuple to existing `retry_if_exception_type` | B: Use `retry_if_exception` with `classify_error` | C: Catch `TransportError` (broad parent) |
|-----------|---|----|---|
| Complexity | 1 line change | Adds dependency on `classify_error` to transport layer | 1 line change |
| Precision | Retries exactly `ConnectError` + `TimeoutException` + `HTTPStatusError` | Retries anything `classify_error` calls TRANSIENT | Also retries `ProtocolError`, `ProxyError`, `ReadError` etc. — too broad |
| KISS | High | Medium | High but over-retries |
| Consistency with `errors.py` | Partial — matches transient network types explicitly | Full — reuses central classifier | Partial — catches more than intended |
| Risk | Low — well-understood tenacity API | Medium — couples transport to error classifier | Medium — retries unrecoverable `ProtocolError` |

### 3.3 Wait strategy impact

`wait_retry_after` only extracts `Retry-After` from `HTTPStatusError` responses. For `ConnectError`/`TimeoutException` (which have no response), it falls back to the `fallback_strategy` (exponential backoff: 1s → 2s → 4s, capped at 30s). This is correct — no change needed.

## 4. Recommendation (.90 confidence)

**Option A** — pass a tuple to `retry_if_exception_type`:

```python
retry = retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException))
```

Rationale: simplest change, precise targeting, no new dependencies, aligns with httpx exception hierarchy. Option B (reusing `classify_error`) would couple the transport layer to the error module unnecessarily (YAGNI). Option C is too broad — `ProtocolError` and `ProxyError` are not transient.

Risk: Retrying `TimeoutException` on a 600s total timeout (the current `httpx.Timeout(600, connect=5)`) means 3 × 600s worst case before failure. Mitigation: `TimeoutException` includes `ConnectTimeout` (5s connect timeout, fast) and `ReadTimeout`/`WriteTimeout` (600s, slow). In practice, connect timeouts are the common transient case. The 600s read timeout is intentional for LLM streaming. If a full read timeout fires, retrying is questionable but harmless (the stop policy caps at 3 attempts).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement ConnectError/TimeoutException retry in copilot transport" --priority needed --status backlog --tags "resilience,auth,phase-11" --body "Add httpx.ConnectError and httpx.TimeoutException to retry_if_exception_type tuple in _build_retry_transport(). Update docstring. See docs/research/copilot-retry-network-errors.md §4. AC: (1) retry_if_exception_type covers HTTPStatusError, ConnectError, TimeoutException. (2) Existing transient-code tests still pass. (3) New tests: mock ConnectError → verify retry occurs then succeeds. (4) New tests: mock TimeoutException → verify retry occurs then succeeds. (5) New tests: mock ConnectError × 3 → verify re-raise after exhaustion."
```

```
kanban\kanban-md.exe create "Update test_retry_only_on_http_status_error to cover network exceptions" --priority needed --status backlog --tags "resilience,test,phase-11" --body "test_providers_copilot.py::TestRetryConfig::test_retry_only_on_http_status_error asserts retry config is retry_if_exception_type for HTTPStatusError only. After #469 implementation this test must be updated to verify the tuple includes all three types. See docs/research/copilot-retry-network-errors.md §5. AC: (1) Test verifies retry config matches (HTTPStatusError, ConnectError, TimeoutException). (2) Integration tests for ConnectError/TimeoutException retry + exhaustion."
```

## 6. Attribution

See Sources table above — all external. No code was copied; only API documentation was referenced.
