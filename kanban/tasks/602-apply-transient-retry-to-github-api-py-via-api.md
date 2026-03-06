---
id: 602
title: Apply TRANSIENT_RETRY to github_api.py via _api_request helper
status: archived
priority: needed
created: 2026-03-06T12:13:05.1228333+01:00
updated: 2026-03-06T19:28:29.8830325+01:00
started: 2026-03-06T13:46:50.4835934+01:00
completed: 2026-03-06T19:28:29.8830325+01:00
tags:
    - resilience
    - tooling
depends_on:
    - 600
class: standard
---

Extract HTTP calls in `GitHubToolset` into a shared `_api_request` helper method, decorate it with `TRANSIENT_RETRY`. All 4 public methods (`create_pr`, `list_prs`, `list_issues`, `get_issue`) delegate HTTP work to it.

### AC
- [ ] New private method `_api_request(self, method: str, url: str, **kwargs) -> httpx.Response` decorated with `TRANSIENT_RETRY`
- [ ] `create_pr`, `list_prs`, `list_issues`, `get_issue` delegate HTTP call to `_api_request`
- [ ] Existing `httpx.Timeout(15, connect=5)` preserved
- [ ] Existing error-string return pattern (`resp.status_code >= 400 -> 'error: ...'`) stays in the public methods, not in `_api_request`
- [ ] `_api_request` raises on transient errors (so tenacity can catch them) but returns `httpx.Response` on success
- [ ] Test: `httpx.MockTransport` returning `ConnectError` once then 200  verify retry + correct result
- [ ] Test: `httpx.MockTransport` returning 422  verify 1 call only, error string returned
- [ ] `create_pr` idempotency note: GitHub returns 422 if PR already exists with same head/base  this is PERMANENT, not retried (safe)

### Architecture notes
- DRY: 4 endpoints repeat identical `async with httpx.AsyncClient(...) as client`  extract once
- `_api_request` handles only the HTTP call; response interpretation stays in each tool method
- See `docs/retry-decorators-research.md` §3.6
