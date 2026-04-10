---
id: 796
title: AUTHENTICATED_WEB source type and ContentFetcher protocol
status: backlog
priority: important
created: '2026-04-10T12:31:51.950715+00:00'
updated: '2026-04-10T12:31:51.950715+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 792
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `models.py` `SourceType` includes `AUTHENTICATED_WEB`
- `protocol.py` defines `ContentFetcher` protocol (runtime-checkable): `async fetch(url: str) -> FetchResult`
- `refresh.py` adds `_handle_authenticated_web()` handler dispatched by `source_type`
- `refresh.py` `RefreshOrchestrator.__init__()` accepts optional `content_fetcher: ContentFetcher | None`
- All #792 tests pass
- Files: `serve/knowledge/src/owlbear_knowledge/models.py`, `protocol.py`, `refresh.py`

## Context
- WS-D: Pipeline Integration
- Scope items 3+4 from #775
