# Retry Decorators for Unretried External Calls

> **Owning task:** #470 — Add retry decorators to unretried external calls
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

Audit finding R-4 identified 5 modules with external HTTP calls lacking retry:
`auth/copilot.py` (3), `tools/github_api.py` (4), `channels/slack.py`
(`chat_postMessage` ×2 + `files_upload_v2`), `memory/knowledge/intake.py`
(`read_url`), `tools/web_search.py` (`_web_read`). Additionally,
`bookmark_pipeline.py:_default_web_read` has the same gap.

**Key questions:** (1) Should all calls get retry? Which are idempotent?
(2) Shared helper or per-function decorator? (3) How to test without real APIs?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | .95 — canonical retry API |
| 2 | Slack SDK RetryHandler | <https://docs.slack.dev/tools/python-slack-sdk/web/#retryhandler> | .85 — built-in `ConnectionErrorRetryHandler` + `RateLimitErrorRetryHandler` |
| 3 | OwlBear `providers/copilot.py` | (local) `src/owlbear/providers/copilot.py` | .90 — existing retry-transport pattern |
| 4 | OwlBear `tools/hooked.py` | (local) `src/owlbear/tools/hooked.py` | .90 — existing `@retry` decorator pattern |
| 5 | OwlBear `core/errors.py` | (local) `src/owlbear/core/errors.py` | .90 — `classify_error` + `_is_transient` |
| 6 | AWS exponential backoff + jitter | <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/> | .80 — jitter best practice |

## 3. Analysis

### 3.1 Idempotency Assessment

| Call site | Method | Idempotent? | Safe to retry? |
|-----------|--------|-------------|----------------|
| `auth/copilot.py:request_device_code` | POST | Yes — creates new device code each time, no side effect | Yes |
| `auth/copilot.py:poll_for_access_token` | POST | Yes — polling is inherently idempotent | Yes (already retries via loop) |
| `auth/copilot.py:exchange_for_copilot_token` | GET | Yes | Yes |
| `github_api.py:create_pr` | POST | **No** — creates a duplicate PR on retry | **Transient-only** (429/502/503/504 + connect errors) |
| `github_api.py:list_prs` | GET | Yes | Yes |
| `github_api.py:list_issues` | GET | Yes | Yes |
| `github_api.py:get_issue` | GET | Yes | Yes |
| `slack.py:send` (chat_postMessage) | POST | **No** — duplicate message on retry | **Transient-only** (connection errors; Slack SDK handles 429) |
| `slack.py:send_blocks` (chat_postMessage) | POST | **No** — duplicate message | **Transient-only** |
| `slack.py:send_image` (files_upload_v2) | POST | **No** — duplicate upload | **Transient-only** (already in try/except) |
| `intake.py:read_url` | GET | Yes | Yes |
| `web_search.py:_web_read` | GET | Yes | Yes |
| `bookmark_pipeline.py:_default_web_read` | GET | Yes | Yes |

**Key finding:** Non-idempotent calls (create_pr, chat_postMessage,
files_upload_v2) must only retry on **transient connection errors** — never on
HTTP 4xx/5xx where the server may have already processed the request. For
connection errors the request never reached the server, so retry is safe.

### 3.2 Implementation Approach

| Option | Description | Confidence |
|--------|-------------|------------|
| A. Shared `_transient_retry` decorator | Module-level constant like existing `HookedToolset` pattern | **.85** |
| B. Per-function inline `@retry(...)` | Duplicate config on each function | .50 |
| C. Shared helper module (`core/retry.py`) | Centralize all retry policies | .75 |

**Recommendation (.85): Option A** — Define a single `_transient_retry`
constant per module (or a shared one in `core/retry.py` if >2 modules reuse
identical config). This matches the existing `HookedToolset` precedent while
keeping changes minimal.

However, since 5+ modules need the same policy, **Option C** (shared helper
in `core/retry.py`) is actually the cleanest approach to avoid duplication.
A single `TRANSIENT_RETRY` object can be imported everywhere.

**Revised recommendation (.90): Option C** — Create `core/retry.py` exporting
a reusable tenacity `@retry` decorator for external HTTP calls.

### 3.3 Retry Policy Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `stop` | `stop_after_attempt(3)` | Matches existing HookedToolset + copilot transport |
| `wait` | `wait_exponential_jitter(initial=1, max=30, jitter=5)` | AWS best practice; jitter prevents thundering herd |
| `retry` | `retry_if_exception(_is_transient_http)` | Uses `classify_error` for consistency |
| `reraise` | `True` | Caller sees original exception, not `RetryError` |
| `before_sleep` | `before_sleep_log(logger, WARNING)` | Visibility into retries |

### 3.4 Slack SDK Consideration

Slack SDK's `AsyncWebClient` already has a built-in `ConnectionErrorRetryHandler`
(1 retry with backoff+jitter). Adding `RateLimitErrorRetryHandler` handles 429.
**Two options:**

| Option | Pros | Cons |
|--------|------|------|
| Use SDK retry handlers | Native, respects Retry-After header | Different mechanism from rest of codebase |
| Use tenacity on our `send`/`send_blocks` | Consistent with rest of codebase | Doesn't respect Slack's Retry-After |

**Recommendation (.80):** Enable Slack SDK's `RateLimitErrorRetryHandler` for
429s (it reads `Retry-After`) AND wrap our `send`/`send_blocks` methods with
the shared tenacity decorator for connection errors only. This gives best of
both worlds. The SDK already handles connection errors once — adding tenacity
on top gives a total of 1 (SDK) + 3 (tenacity) = 4 attempts, which is
reasonable for an always-on daemon.

**Simpler alternative (.85):** Just add the SDK's
`RateLimitErrorRetryHandler(max_retry_count=1)` to the `AsyncWebClient`
constructor and don't add tenacity to Slack methods at all — the SDK already
retries connection errors once. This keeps Slack retry logic in Slack's domain.

### 3.5 `poll_for_access_token` — Already Has Retry

`poll_for_access_token` already implements its own retry loop (polling with
sleep). Adding tenacity would create double-retry. **Exclude it from scope.**

### 3.6 `_web_read` Error Handling Pattern

`_web_read` already catches `httpx.TimeoutException` and `httpx.HTTPStatusError`
and returns human-friendly error strings (no exception raised). Tenacity
`@retry` only intercepts exceptions. Two options:

| Option | Approach | Confidence |
|--------|----------|------------|
| Wrap the `httpx.AsyncClient` block only | Retry the HTTP call, not the trafilatura extraction | **.85** |
| Extract HTTP fetch into a helper | `_fetch_url(url) -> httpx.Response`, apply retry there | .80 |

**Recommendation (.85):** Extract the HTTP fetch into a small inner function
decorated with `@retry`, keeping the existing error-string-return pattern in
the outer `_web_read`.

## 4. Recommendation (.90 confidence)

1. **Create `src/owlbear/core/retry.py`** exporting:
   - `TRANSIENT_RETRY` — a pre-configured `@retry` decorator for async
     functions making external HTTP calls (3 attempts, exp backoff + jitter,
     transient-only, reraise, log before sleep).
   - `_is_transient_http(exc)` — predicate using `classify_error` for httpx
     errors (ConnectError, TimeoutException, HTTPStatusError with 429/502/503/504).

2. **Apply to httpx call sites:**
   - `auth/copilot.py`: Decorate `request_device_code` and
     `exchange_for_copilot_token`. Skip `poll_for_access_token` (own loop).
   - `tools/github_api.py`: Extract HTTP calls into an `_api_request` helper
     method, decorate it. All 4 tools delegate to it.
   - `memory/knowledge/intake.py`: Decorate `read_url`.
   - `tools/web_search.py`: Extract HTTP fetch in `_web_read` into a decorated
     inner function.
   - `bookmark_pipeline.py`: Decorate `_default_web_read` (bonus, not in AC).

3. **Slack SDK retry:** Add `RateLimitErrorRetryHandler(max_retry_count=1)` to
   the `AsyncWebClient` constructor. The SDK's built-in
   `ConnectionErrorRetryHandler` already handles connection errors. No tenacity
   needed on Slack methods.

**Risks:**

- `create_pr` retry on 502/503/504 could create duplicate PRs if server
  processed the request before returning error. Mitigation: GitHub returns 422
  if PR already exists with same head/base, which is a permanent error.
- Tenacity `@retry` on `async def` works natively (verified in docs + existing
  usage in `hooked.py`).

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Create core/retry.py shared transient retry decorator" --status backlog --priority needed --tags "resilience,scope:core,phase-13" --body "Create src/owlbear/core/retry.py exporting TRANSIENT_RETRY decorator (3 attempts, wait_exponential_jitter(initial=1, max=30, jitter=5), retry transient HTTP errors via classify_error, reraise=True, before_sleep_log). Include _is_transient_http predicate. See docs/retry-decorators-research.md §4."

kanban\kanban-md.exe create "Apply retry to auth/copilot.py external calls" --status backlog --priority needed --tags "resilience,auth,phase-13" --depends-on 470 --body "Decorate request_device_code and exchange_for_copilot_token with TRANSIENT_RETRY from core/retry.py. Skip poll_for_access_token (has own retry loop). Test with respx mocking transient errors. See docs/retry-decorators-research.md."

kanban\kanban-md.exe create "Apply retry to github_api.py external calls" --status backlog --priority needed --tags "resilience,tooling,phase-13" --depends-on 470 --body "Extract HTTP calls in GitHubToolset into _api_request helper, decorate with TRANSIENT_RETRY. All 4 tools (create_pr, list_prs, list_issues, get_issue) delegate to it. Test with httpx mock transport. See docs/retry-decorators-research.md."

kanban\kanban-md.exe create "Enable Slack SDK RateLimitErrorRetryHandler" --status backlog --priority needed --tags "resilience,scope:core,phase-13" --depends-on 470 --body "Add RateLimitErrorRetryHandler(max_retry_count=1) to AsyncWebClient constructor in channels/slack.py. SDK already handles connection errors. No tenacity needed. Test with mock SlackApiError(429). See docs/retry-decorators-research.md."

kanban\kanban-md.exe create "Apply retry to intake.py read_url and web_search.py _web_read" --status backlog --priority needed --tags "resilience,scope:core,phase-13" --depends-on 470 --body "Decorate intake.read_url with TRANSIENT_RETRY. In web_search._web_read, extract HTTP fetch into inner function with retry (keep error-string-return pattern). Bonus: decorate bookmark_pipeline._default_web_read. Test with respx. See docs/retry-decorators-research.md."
```

## 6. Testing Strategy

All retry tests use **mock transports / respx** — no real API calls:

| Module | Test approach |
|--------|--------------|
| `core/retry.py` | Unit test `_is_transient_http` with each httpx exception type. Test `TRANSIENT_RETRY` decorator with a mock async function that fails N times then succeeds. |
| `auth/copilot.py` | `respx` mock returning 502 twice then 200. Verify 3 calls made. |
| `github_api.py` | `httpx.MockTransport` returning `ConnectError` then success. Verify retry + correct result. |
| `channels/slack.py` | Mock `AsyncWebClient` with SDK `RateLimitErrorRetryHandler`. Verify 429 is retried. |
| `intake.py` / `web_search.py` | `respx` mock with transient failure then success. Verify content returned. |
