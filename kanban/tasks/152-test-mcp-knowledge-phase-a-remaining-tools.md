---
id: 152
title: 'Test: mcp-knowledge Phase A remaining tools'
status: review
priority: needed
created: 2026-03-29T19:20:21.3798812+02:00
updated: 2026-03-30T10:11:32.8190266+02:00
tags:
    - phase-1
    - scope:mcp
    - scope:knowledge
    - test
class: standard
---

## Objective
Write failing tests (TDD RED) for the remaining mcp-knowledge Phase A tools not covered by existing test files: search_knowledge (v2 query() API), list_sources, and knowledge://stats resource.

## Acceptance Criteria

### search_knowledge v2 API tests (in packages/mcp-knowledge/tests/test_search_v2.py)
- [ ] Test search_knowledge returns formatted bullet list for valid query: mocks KnowledgeQueryService.query() returning list[StructuredSearchResult]; verifies output contains bullet lines
- [ ] Test each bullet follows "- {title} ({score:.2f}): {snippet[:200]}" format
- [ ] Test search_knowledge returns "No relevant knowledge found." when query() returns empty list
- [ ] Test search_knowledge returns "Knowledge service not available." when query_service is None
- [ ] Test search_knowledge awaits query() directly (not via asyncio.to_thread) since query() is async
- [ ] Test limit param maps to top_k kwarg on query()

### list_sources tests (in packages/mcp-knowledge/tests/test_list_sources.py)
- [ ] Test list_sources returns formatted bullet list "- {name} ({source_type}): scope={scope}" with mocked KnowledgeSourceStore.list_all
- [ ] Test list_sources with scope filter passes scope to list_all(scope=scope)
- [ ] Test list_sources without scope passes None to list_all
- [ ] Test list_sources returns "No sources found." when result is empty
- [ ] Test list_sources calls list_all via asyncio.to_thread (sync method)

### knowledge://stats resource tests (in packages/mcp-knowledge/tests/test_stats_resource.py or appended to test_search_v2.py)
- [ ] Test knowledge://stats resource is registered on the mcp instance
- [ ] Test resource returns format matching get_stats: "Knowledge base: {n} documents, {n} entities, {n} edges"

### General
- [ ] All new tests FAIL (RED phase)
- [ ] ruff clean on test files
- [ ] All tests mock KnowledgeQueryService, KnowledgeSourceStore, GraphStore (no real DB, Qdrant, or embeddings)
- [ ] Imports from owlbear_mcp_knowledge.server (not tools.py)

## Context
Depends on #16 AC for tool interfaces. Existing test_search_knowledge.py tests the old tools.py function (query_for_context API); these new tests target server.py's search_knowledge with v2 query() API returning list[StructuredSearchResult]. StructuredSearchResult fields: doc_id, title, score, snippet, entity_type, scope.

[[2026-03-29]] Sun 20:01
## Architecture Review (cycle 1)
**Verdict:** BLOCK (ideation)

Empty/unscoped body. Task has no acceptance criteria, no list of which tools constitute 'Phase A remaining', no research doc reference, and no coverage targets. Missing body content alone is reason to refuse per agent-common rules on placeholder and unscoped task rejection.

To unblock: re-create or edit with concrete AC specifying (1) which MCP-knowledge tools are in scope, (2) interface contracts each tool must satisfy, (3) test coverage targets, and (4) reference to any research doc.

[[2026-03-30]] Mon 09:25
## Test-Writer Notes
- Test files: packages/mcp-knowledge/tests/test_search_v2.py, test_list_sources.py, test_stats_resource.py
- Classes: TestFromAC_SearchKnowledgeV2, TestFromAC_ListSources, TestFromAC_KnowledgeStatsResource
- Tests per category: happy 4, edge 2, error 2, boundary 1
- Total: 9 tests FAIL + 1 collection error (ImportError for list_sources) - all RED
- ruff: clean
- AC coverage: bullet format (2), snippet truncation (1), multiple results (1), empty list (1), query() awaited (1), limit top_k (1), list_sources all 5 AC lines (ImportError), stats registered (1), stats format (1)
- OMITTED: 'qs is None - service unavailable' from test_search_v2.py - tests unchanged behavior, would be GREEN in RED phase

[[2026-03-30]] Mon 10:11
## Builder Notes
- Files changed: packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Tests: 14 passed (7 search_v2, 5 list_sources, 2 stats_resource), coverage 96% on server.py
- Lint: ruff clean
- Evidence: all TestFromAC_* classes GREEN, no modifications to test files
- Fixes applied: search_knowledge v2 (await qs.query), list_sources new tool, knowledge_stats(ctx) callable + knowledge_stats_resource() stub for URI registration
