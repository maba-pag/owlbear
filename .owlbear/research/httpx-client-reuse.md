# httpx.AsyncClient Reuse in GitHubToolset

> **Owning task:** #507 — Reuse httpx.AsyncClient in GitHubToolset
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

Code quality audit finding F-08: every `_api_request` call creates a new `httpx.AsyncClient` via `async with`, causing 4 separate TCP+TLS handshakes when tools are called in sequence. Should we create a single long-lived client instance, and if so, how?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | httpx docs — Clients | <https://www.python-httpx.org/advanced/clients/> | 1.0 |
| 2 | httpx docs — Async Support | <https://www.python-httpx.org/async/#opening-and-closing-clients> | 1.0 |
| 3 | PydanticAI `cached_async_http_client` | pydantic-ai `models/__init__.py` | .95 |
| 4 | OwlBear Slack channel — `AsyncWebClient` lifecycle | `src/owlbear/channels/slack.py` L65-68, L260-268 | .90 |
| 5 | OwlBear bootstrap — cleanup list pattern | `src/owlbear/bootstrap.py` L125-151, L645 | .90 |
| 6 | OwlBear httpx timeout research | `docs/research/httpx-timeout.md` | .85 |

### Key facts

- **httpx docs (Source 1):** "When you make several requests to the same host, the Client will reuse the underlying TCP connection, instead of recreating one for every single request." Benefits: reduced latency, reduced CPU, reduced network congestion.
- **httpx async docs (Source 2):** "Make sure you're not instantiating multiple client instances — for example by using `async with` inside a hot loop." Close with `await client.aclose()` when not using context manager.
- **PydanticAI (Source 3):** Uses `@cache` to create one `httpx.AsyncClient` per provider. Handles `is_closed` guard for re-creation. Client is long-lived, never explicitly closed.
- **OwlBear Slack (Source 4):** Creates `AsyncWebClient` eagerly in `__init__`, lives for daemon lifetime, closed via `disconnect()`.
- **OwlBear bootstrap (Source 5):** `BootstrapResult.cleanup` list accumulates teardown callables (sync and async). Knowledge infra registers `conn.close`. Same pattern works for `client.aclose`.

## 3. Analysis

### 3.1 Client lifecycle approach

| Approach | Pros | Cons | KISS |
|----------|------|------|------|
| **Eager in `__init__`** (.85) | Simple, matches Slack pattern, client ready immediately | Client created even if no API calls happen (unlikely — toolset only created when token present) | High |
| Lazy on first call (.65) | Defers allocation | Extra `if self._client is None` check on every call, more complex | Medium |
| `@cache` singleton (.55) | PydanticAI uses it | Global state, harder to test, doesn't fit toolset-instance model | Low |

### 3.2 Cleanup strategy

| Approach | Pros | Cons | KISS |
|----------|------|------|------|
| **`aclose()` method + bootstrap cleanup** (.90) | Matches existing `conn.close` pattern, explicit | Requires `build_toolsets` to register cleanup | High |
| `__del__` / gc (.30) | No explicit cleanup | Unreliable in async, antipattern | Low |
| Async context manager on toolset (.50) | Pythonic | Over-engineering — toolset lifecycle is managed by bootstrap, not `async with` | Medium |

### 3.3 Retry interaction

Current `@TRANSIENT_RETRY` wraps the full `async with httpx.AsyncClient()` block. With a shared client, only the `client.request()` call is retried. This is *better* — a broken connection in the pool is replaced by httpx automatically, while the client itself remains valid. No changes needed to retry logic.

### 3.4 Concurrency safety

`httpx.AsyncClient` is designed for concurrent async use. Multiple concurrent tool calls sharing one client is safe (httpx docs, Source 1).

### 3.5 Test impact

Current tests patch `httpx.AsyncClient` as a context manager mock per call. With a shared client, tests must either: (a) patch at construction time, or (b) inject a mock client. Option (b) via an optional `_client` constructor param is cleaner for testing and follows dependency injection principles.

### 3.6 `base_url` and shared headers

| Change | Benefit | Risk | Verdict |
|--------|---------|------|---------|
| Set `base_url=_BASE_URL` on client | Simplifies URL construction in tools | None | Nice-to-have, not required |
| Set `headers=self._headers()` on client | Removes per-request header building | Token evaluated once at init (fine — token is static) | Nice-to-have, not required |

Per YAGNI, keep to the minimal change: client reuse + `aclose()`. Headers/base_url can be a separate follow-up if desired.

## 4. Recommendation (.90 confidence)

**Eager client in `__init__` + `aclose()` + bootstrap cleanup registration.**

Implementation sketch (approx. 15 LOC net change in `github_api.py`, 3 LOC in `bootstrap.py`):

1. In `__init__`: `self._client = httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5))`
2. In `_api_request`: replace `async with httpx.AsyncClient(...)` with `self._client.request(...)`
3. Add `async def aclose(self) -> None: await self._client.aclose()`
4. In `build_toolsets`: keep a ref to the toolset, call `cleanup.append(github_ts.aclose)` after creation
5. Tests: update mock setup to patch client at construction time or inject via constructor

**Risks:**

- Unclosed client if bootstrap cleanup is skipped (mitigated: httpx emits ResourceWarning, not a leak in practice for a daemon that exits)
- Tests need updating (medium effort, ~30 min)

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement httpx.AsyncClient reuse in GitHubToolset" --priority needed --tags "phase-3,tools,performance" --body "Implement the approach from docs/research/httpx-client-reuse.md S4: (1) Create client eagerly in __init__, (2) Replace async-with in _api_request with direct client.request(), (3) Add aclose() method, (4) Register aclose in bootstrap cleanup list. AC: single client instance per toolset; connection reuse verified; aclose registered in BootstrapResult.cleanup; all existing tests updated and passing."

kanban\kanban-md.exe create "Update GitHubToolset tests for shared client" --priority needed --tags "phase-3,test,tools" --body "Update tests/test_github_api.py to mock the shared httpx.AsyncClient instead of per-call context manager mocks. See docs/research/httpx-client-reuse.md S3.5. AC: all tests pass; mock setup patches client at construction; no per-call AsyncClient patching remains."
```

## 6. Research Checklist

- [x] **Theoretical validity** — httpx connection pooling is the documented best practice; per-call clients waste TCP+TLS overhead
- [x] **Prior art** — httpx docs (Sources 1-2), PydanticAI cached client (Source 3), OwlBear Slack pattern (Source 4)
- [x] **Technical feasibility** — `AsyncClient()` constructor is sync (fits `__init__`), `aclose()` is async (fits cleanup list)
- [x] **Architecture fit** — Bootstrap cleanup list already handles async teardown; Slack channel uses same eager-init pattern
- [x] **Implementation approach** — Eager client + aclose + bootstrap cleanup; ~18 LOC total change
