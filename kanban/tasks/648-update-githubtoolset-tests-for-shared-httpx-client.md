---
id: 648
title: Update GitHubToolset tests for shared httpx client
status: archived
priority: important
created: 2026-03-07T19:36:54.7411598+01:00
updated: 2026-03-09T22:43:56.9468327+01:00
started: 2026-03-07T22:55:33.8397052+01:00
completed: 2026-03-09T22:43:56.9468327+01:00
tags:
    - test
    - tools
    - audit
class: standard
---

Companion test task for #507. Update tests/test_github_api.py mocking strategy for shared client.

## Acceptance Criteria

1. _make_client helper no longer sets __aenter__/__aexit__  mock is a plain AsyncMock with .request
2. Patching targets GitHubToolset._client attribute (or injects mock client via constructor param) instead of patching httpx.AsyncClient as context manager
3. All existing test classes pass: TestConstructorValidation, TestToolRegistration, TestParseGitRemote, TestCreatePr, TestListPrs, TestListIssues, TestGetIssue, TestApiRequestRetry
4. New test: constructing GitHubToolset creates self._client as httpx.AsyncClient instance
5. New test: aclose() calls self._client.aclose()
6. New test: two sequential API calls reuse the same client (client.request called twice, no new AsyncClient created)
7. ruff check clean on test_github_api.py

## Architecture Notes

- Prefer injecting mock client via constructor (optional _client param) over monkeypatching  cleaner DI for tests
- See docs/httpx-client-reuse-research.md S3.5

[[2026-03-09]] Mon 22:43
## Audit
### AC Verification

| AC | Evidence | Status |
|---|---|---|
| 1. _make_client no __aenter__/__aexit__ | Lines 68-72: AsyncMock(spec=httpx.AsyncClient) with .request/.aclose only | PASS |
| 2. Inject mock via constructor | _toolset helper accepts _client param, all tests use DI | PASS |
| 3. All 8 existing test classes pass | 47 passed in 3.13s | PASS |
| 4. New test: constructor creates httpx.AsyncClient | test_constructor_creates_httpx_client L628 | PASS |
| 5. New test: aclose() delegates | test_aclose_calls_client_aclose L632 | PASS |
| 6. New test: client reuse | test_two_api_calls_reuse_same_client L639 | PASS |
| 7. ruff clean | All checks passed | PASS |

### Test Results
- pytest (scoped): 47 passed in 3.13s
- pytest (full): 1182 passed, 1 failed (pre-existing, unrelated test_context_hydration), 2 skipped
- ruff: All checks passed

### Confidence: .97
### Action: archive
