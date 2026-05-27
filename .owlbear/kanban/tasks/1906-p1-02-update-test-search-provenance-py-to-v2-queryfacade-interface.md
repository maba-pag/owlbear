---
id: 1906
title: 'P1-02: Update test_search_provenance.py to v2 QueryFacade interface'
status: backlog
priority: needed
created: 2026-05-28T00:34:20.718643+02:00
updated: 2026-05-28T00:34:26.205013+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - test_search_provenance.py no longer references query_service or constructs 
    AppContext with removed fields
  - test_search_provenance.py mocks QueryFacade.search() (or equivalent v2 
    interface) instead of query_service.query()
  - pytest tests/test_search_provenance.py passes (0 failures, 0 errors)
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Update the durable module-level `tests/test_search_provenance.py` (~28 tests) to test the provenance serialization contract against the v2 QueryFacade interface instead of the removed `query_service` path.

## Current State
- Builds a `query_service`-only context via `_make_ctx(query_service=...)` and calls `qs.query()`
- Tests provenance fields: retrieval_path, entities, related_sources, source
- The provenance contract itself is valid — only the interface changed from `query_service` → `QueryFacade`

## Direction
- Replace `_make_ctx(query_service=...)` with a context mock providing `query_facade` (matching current AppContext shape)
- Update mock targets from `query_service.query()` → `QueryFacade.search()` return values
- Preserve the provenance serialization assertions (they test `knowledge_search` tool output)
- If the provenance contract is now fully covered by `serve/mcp-knowledge/tests/`, retire the file with a note explaining supersession

## Scope
- In-scope: rewrite or retire `tests/test_search_provenance.py`
- Out-of-scope: other test files, server.py changes