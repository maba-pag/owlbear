---
id: 54
title: Implement real search_knowledge tool in mcp-knowledge
status: ideation
priority: needed
created: 2026-03-26T19:12:42.1178047+01:00
updated: 2026-03-29T12:45:26.9842278+02:00
tags:
    - phase-2
    - scope:mcp
    - scope:knowledge
depends_on:
    - 40
    - 72
blocked: true
block_reason: 'v1/v2 API mismatch: AC built on query_for_context (v1) but v2 has async query() returning StructuredSearchResult. Re-research needed against v2 API.'
class: standard
---

## Objective
Replace the placeholder search_knowledge tool in mcp-knowledge with a real implementation that delegates to KnowledgeQueryService.query_for_context().

## Acceptance Criteria
- [ ] search_knowledge tool calls KnowledgeQueryService.query_for_context(query, top_k=limit) via asyncio.to_thread() (non-blocking; service is synchronous)
- [ ] Tool returns the pre-formatted string from query_for_context() directly (document titles and relevant snippets within token budget)
- [ ] When query_for_context() returns None, tool returns the string 'No relevant knowledge found for your query.'
- [ ] When AppContext.query_service is None (service not initialized), tool returns the string 'Knowledge service not available.'
- [ ] app_lifespan wires real KnowledgeQueryService: init_db(), GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider, KnowledgeQueryService composed and yielded via AppContext.query_service
- [ ] app_lifespan closes the sqlite3 connection in its finally block
- [ ] All tests from preceding test task #72 pass GREEN

## Context
Depends on #40 (scaffold). See docs/research/search-knowledge-tool-impl.md for API analysis.
query_for_context() catches all exceptions internally, returns None on failure. No additional try/except needed in the tool layer.
Follow-up #70 adds search_structured() for richer output (scores, entity types) if needed later.

## Research
Doc: docs/research/search-knowledge-tool-impl.md
Key findings: AC mismatch (no search() method, actual API is query_for_context()), sync/async boundary requires asyncio.to_thread(), AC2 needs refinement. Follow-up: #70. Recommendation (.80): Use query_for_context() as-is.

## Architecture Review
**Verdict:** REFINE

### AC Assessment
See docs/scratch/54-architect.md for full assessment table.

### Architecture Notes
Pattern follows Qdrant MCP server: sync service wrapped in asyncio.to_thread() for MCP async context. query_for_context() is the correct public API (query_service.py L83-99). Tool layer is thin: delegate + format None case.
Module layering: mcp-knowledge (MCP layer) depends on owlbear-knowledge (memory layer). No upward imports.
Lifespan wiring composes: init_db, GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider, KnowledgeQueryService. All sync, suitable for lifespan-managed DI.

### Changes Made
- Rewrote AC from 5 vague/incorrect items to 7 precise verifiable items
- Fixed API reference: search() to query_for_context()
- Relaxed output format to match actual API (structured output deferred to #70)
- Added asyncio.to_thread() requirement
- Added lifespan wiring AC
- Added depends_on: #40 (scaffold), #72 (TDD RED)
- Created #72: Test task for search_knowledge tool with 7 test scenarios

### Dependencies
- Added: #40 (scaffold mcp-knowledge) must complete first
- Added: #72 (TDD RED test task) must complete before builder
- Verified: #70 (search_structured) at ideation, correctly deferred
