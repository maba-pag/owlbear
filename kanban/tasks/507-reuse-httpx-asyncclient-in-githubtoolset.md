---
id: 507
title: Reuse httpx.AsyncClient in GitHubToolset
status: archived
priority: important
created: 2026-03-04T07:38:19.232432+01:00
updated: 2026-03-09T21:10:00.9211308+01:00
started: 2026-03-06T23:40:08.9526803+01:00
completed: 2026-03-09T21:10:00.9211308+01:00
tags:
    - audit
    - performance
    - tools
depends_on:
    - 648
class: standard
---

F-08: Each _api_request call creates a new httpx.AsyncClient. 4 separate TCP+TLS negotiations in sequence.
See docs/research/httpx-client-reuse.md for research (~18 LOC change).

## Acceptance Criteria

1. GitHubToolset.__init__ creates a single httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5)) stored as self._client
2. _api_request uses self._client.request() directly instead of async-with httpx.AsyncClient()  no per-call client construction
3. GitHubToolset exposes async def aclose() -> None that calls await self._client.aclose()
4. bootstrap.build_toolsets registers github_toolset.aclose in the cleanup list (same pattern as infra.conn.close at bootstrap.py L658)
5. @TRANSIENT_RETRY remains on_api_request  no changes to retry decorator or logic
6. _headers() continues to be called per-request (not baked into client constructor)  keeps current behavior
7. All existing tests in test_github_api.py pass (mocking strategy updated per companion test task)
8. ruff check clean on github_api.py and bootstrap.py

## Architecture Notes

- Pattern: follows Slack channel eager-init (channels/slack.py) and bootstrap cleanup-list pattern (bootstrap.py L658)
- httpx.AsyncClient constructor is sync  fits __init__
- httpx.AsyncClient is concurrency-safe for async  multiple concurrent tool calls are fine
- No base_url or shared headers on client (YAGNI per research S3.6)
- depends_on: #648 (test task)

[[2026-03-09]] Mon 21:09
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| 1. __init__ creates single httpx.AsyncClient(timeout=Timeout(15,connect=5)) stored as self._client | github_api.py L109: `self._client = _client or httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5))` | PASS |
| 2. _api_request uses self._client.request() directly, no per-call client | github_api.py L143: `return await self._client.request(method, url, headers=self._headers(), **kwargs)` — no `async with` | PASS |
| 3. aclose() calls self._client.aclose() | github_api.py L146: `async def aclose` → `await self._client.aclose()` | PASS |
| 4. bootstrap registers github_toolset.aclose in cleanup list | toolsets.py L312: `cleanup.append(github_toolset.aclose)` | PASS |
| 5. @TRANSIENT_RETRY remains on _api_request | github_api.py L135: `@TRANSIENT_RETRY` decorator present | PASS |
| 6. _headers() called per-request, not baked into client | github_api.py L143: `headers=self._headers()` in each request call | PASS |
| 7. All tests in test_github_api.py pass | 47 passed in 7.51s | PASS |
| 8. ruff check clean on github_api.py and bootstrap/toolsets.py | `All checks passed!` on both files + tests | PASS |

### Test Results
- pytest (scoped): 47/47 passed (test_github_api.py)
- pytest (regression): 211 passed (github_api + bootstrap + bootstrap_integration + bootstrap_structure)
- Full suite: numpy import stall (environment issue, unrelated to #507)
- ruff: All checks passed

### Confidence: .97
### Action: archive
