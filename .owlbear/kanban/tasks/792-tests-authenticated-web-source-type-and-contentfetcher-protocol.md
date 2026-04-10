---
id: 792
title: Tests — AUTHENTICATED_WEB source type and ContentFetcher protocol
status: backlog
priority: needed
created: '2026-04-10T12:31:33.745249+00:00'
updated: '2026-04-10T12:31:33.745249+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on:
- 785
- 787
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `AUTHENTICATED_WEB` is a member of `SourceType`
- Tests verify `ContentFetcher` protocol exists in `protocol.py` with `async fetch(url: str) -> FetchResult` method
- Tests verify `_handle_authenticated_web()` dispatches via ContentFetcher and returns `RefreshResult`
- Tests use mock ContentFetcher — no real browser dependency in tests
- File: `tests/test_authenticated_web_775.py`

## Context
- WS-D: Pipeline Integration
- Scope items 3+4 from #775
