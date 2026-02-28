---
id: 165
title: Test GitHubToolset — httpx GitHub API tools
status: archived
priority: important
created: 2026-02-27T20:46:56.0796787+01:00
updated: 2026-02-28T23:53:18.3392026+01:00
started: 2026-02-27T21:28:16.5649247+01:00
completed: 2026-02-28T23:53:18.3392026+01:00
tags:
    - phase-8
    - tools
    - github
    - test
class: standard
---

Test task for GitHubToolset. Write tests first (TDD).

## AC
- [ ] File: tests/test_github_api.py
- [ ] Test create_pr: mock httpx POST to /repos/{owner}/{repo}/pulls, verify auth header and request body
- [ ] Test list_prs: mock httpx GET, verify query params (state, per_page)
- [ ] Test list_issues: mock httpx GET, verify state filter
- [ ] Test get_issue: mock httpx GET, verify path param interpolation
- [ ] Test create_pr emits HookEvent.PRE_TOOL_USE before API call
- [ ] Test missing/empty token raises clear error at construction time
- [ ] Test auto-detection of owner/repo from git remote URL (parse https and ssh formats)
- [ ] ruff clean

## Architecture
- Use pytest-httpx or manual httpx mock transport for HTTP mocking
- Follow test_providers_copilot.py pattern for httpx mocking if applicable
- Use pytest-asyncio for async test methods
