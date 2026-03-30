---
id: 34
title: Knowledge package integration + hybrid search
status: todo
priority: needed
created: 2026-03-26T18:33:53.2231299+01:00
updated: 2026-03-30T08:15:34.0924594+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 33
    - 205
class: standard
---

## Objective

Complete the knowledge package by porting graph-augmented retrieval from v1 and wiring hybrid search (graph expansion + vector similarity) into the query service.

## Acceptance Criteria

- [ ] `retrieval.py` with `GraphAugmentedRetriever`:
  - `__init__(vector_store: VectorStoreProtocol, graph_store: GraphStore, embedding_provider: EmbeddingProvider, *, expansion_depth: int = 1, max_expansion_tokens: int = 2000, max_neighbors_per_entity: int = 10, expansion_enabled: bool = True, weight_by_importance: bool = False)`
  - `retrieve(query: str, top_k: int = 5, scopes: list[str] | None = None) -> RetrievalResult`
  - `_embed()` prefers `embed_hybrid` with dense fallback
  - `_resolve_seeds()`: entities where `chunk_id` appears in vector search result IDs
  - `_expand()`: BFS neighbors within `max_expansion_tokens` word-count budget, formatted as `"A --[rel]--> B: desc"`
- [ ] `retrieval.py` with `RetrievalResult` (frozen Pydantic model):
  - Fields: `chunks: list[tuple[str, float]]`, `expansion_text: str`, `entities_found: int`
- [ ] `query_service.py` add `query_for_context(prompt: str, *, max_tokens: int = 2000, top_k: int = 5) -> str | None`:
  - When `GraphAugmentedRetriever` provided at construction: delegates to retriever for chunks + expansion
  - Formats results as `"Relevant knowledge:\n\n- Title: snippet"` within token budget
  - Returns `None` on no results or on exception (existing graceful degradation pattern)
- [ ] `__init__.py` exports `GraphAugmentedRetriever`, `RetrievalResult`
- [ ] Zero PydanticAI imports in any knowledge package module (verified by grep)
- [ ] `packages/knowledge/README.md`: purpose, install command, optional deps (qdrant, embedding), basic usage example
- [ ] `uv pip install -e packages/knowledge/` succeeds

## Architecture Notes

- Port from `v1/src/owlbear/memory/knowledge/retrieval.py`: adapt imports from `owlbear.memory.knowledge.*` to `owlbear_knowledge.*`
- Follow existing DI pattern: constructor injection of stores + providers, no singletons
- `chunker.py` already complete (no changes needed)
- `query_service.py` already has `query()` returning `list[StructuredSearchResult]`: keep that, add `query_for_context()` alongside
- Tests should use manually populated graph fixtures (not extraction pipeline) since #33 provides only stubs

## Context

Depends on #33 (entity extraction) and #205 (TDD RED tests). Subtask 4/4 of knowledge engine extraction. After this, mcp-knowledge (#16) can be built on top.

[[2026-03-30]] Mon 08:15
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| retrieval.py GraphAugmentedRetriever | New module, clear interface, follows v1 pattern | Kept as-is |
| RetrievalResult frozen model | Precise fields specified | Kept as-is |
| query_service.py query_for_context() | Extends existing class, clear contract | Kept as-is |
| __init__.py exports | Standard, verifiable | Kept as-is |
| Zero PydanticAI imports | Verifiable by grep | Kept as-is |
| README.md | Scope clear | Kept as-is |
| Package installable | Verifiable | Kept as-is |

### Architecture Notes
- Port source: v1/src/owlbear/memory/knowledge/retrieval.py (GraphAugmentedRetriever + RetrievalResult)
- Existing patterns to follow: query_service.py DI (constructor injection), protocol.py VectorStoreProtocol, embeddings.py EmbeddingProvider
- chunker.py already fully ported, no changes needed
- query_service.py already has query() returning list[StructuredSearchResult], add query_for_context() alongside
- Module layering: retrieval.py sits alongside query_service.py in knowledge package, depends on protocol.py, graph_store.py, embeddings.py (same-layer, valid)

### Changes Made
- Rewrote AC: removed stale items (chunker.py already done), added precise interface specs for retrieval.py and query_for_context()
- Fixed tag: type:test changed to type:build (AC is build work)
- Created #205: Test: Knowledge package hybrid search + retrieval (TDD RED pair, status: todo)
- Added dependency: #34 depends on #205

### Dependencies
- Verified: #33 (entity extraction) in backlog, stubs exist, full impl needed for real pipeline
- Added: #205 (TDD test task) as dependency
