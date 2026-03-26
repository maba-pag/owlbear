---
id: 309
title: Test WebSearchToolset — mock ddgs and httpx
status: archived
priority: critical
created: 2026-03-01T03:56:47.4428305+01:00
updated: 2026-03-22T18:59:19.6405919+01:00
started: 2026-03-01T05:15:10.6279415+01:00
completed: 2026-03-01T17:09:34.6869627+01:00
tags:
    - phase-11
    - tools
    - test
class: standard
---

Preceding test task for #292 (WebSearchToolset implementation). Write failing tests FIRST per TDD.

## Acceptance Criteria

### Test file: tests/test_web_search.py

- [ ] `TestWebSearchToolset` class with async pytest fixtures
- [ ] Mock `DDGS().text()` returns list of `{title, href, body}` dicts
- [ ] Mock `httpx.AsyncClient.get()` returns fake HTML responses

### web_search tests

- [ ] `test_web_search_returns_formatted_markdown` — formatted numbered list with title, snippet, URL
- [ ] `test_web_search_filters_blocked_urls` — results matching blocked_urls patterns are excluded
- [ ] `test_web_search_respects_allowlist` — only results matching allowed_urls are returned (when set)
- [ ] `test_web_search_handles_rate_limit` — catches RatelimitException, returns informative error string
- [ ] `test_web_search_empty_results` — returns 'No results found.' for empty result sets
- [ ] `test_web_search_num_results_param` — passes num_results to DDGS.text() max_results param

### web_read tests

- [ ] `test_web_read_fetches_and_extracts` — httpx GET + trafilatura extract, returns markdown content
- [ ] `test_web_read_rejects_blocked_url` — raises or returns error for blocked URL before fetching
- [ ] `test_web_read_respects_allowlist` — rejects URL not in allowed_urls (when set)
- [ ] `test_web_read_handles_fetch_timeout` — httpx timeout returns informative error
- [ ] `test_web_read_handles_http_error` — 404/500 returns informative error string
- [ ] `test_web_read_truncates_long_content` — output capped at max_length characters
- [ ] `test_web_read_trafilatura_fallback` — if extraction fails, returns raw text truncated

### Constructor / registration tests

- [ ] `test_constructor_accepts_url_lists` — blocked_urls and allowed_urls stored correctly
- [ ] `test_tools_registered` — toolset has 'web_search' and 'web_read' in .tools dict
- [ ] `test_ddgs_import_guard` — when ddgs not installed, import error is raised at tool call time (not import time)

### Coverage

- [ ] >= 90% coverage on tests/test_web_search.py

### Architecture notes

- Follow test_terminal_tools.py and test_filesystem.py patterns for fixture style
- Use unittest.mock.patch / AsyncMock for ddgs and httpx mocking
- Do NOT import ddgs or trafilatura at module level in tests — mock them
