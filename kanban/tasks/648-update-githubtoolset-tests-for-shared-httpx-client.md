---
id: 648
title: Update GitHubToolset tests for shared httpx client
status: done
priority: important
created: 2026-03-07T19:36:54.7411598+01:00
updated: 2026-03-07T22:55:33.8397052+01:00
started: 2026-03-07T22:55:33.8397052+01:00
completed: 2026-03-07T22:55:33.8397052+01:00
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
