---
id: 162
title: 'Integration test: full ingest-to-search cycle'
status: todo
priority: needed
created: 2026-03-29T19:37:50.9697847+02:00
updated: 2026-03-30T23:03:56.4729425+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:test
depends_on:
    - 158
    - 34
class: standard
---

## Objective
End-to-end integration test: ingest document, extract entities, build graph, embed chunks, search by query.

## Acceptance Criteria

- [ ] Test ingests a text document through `IngestPipeline.ingest()` using a mock `StructuredExtractor` (returning deterministic entities/edges) and mock `EmbeddingProvider` (returning deterministic 1024-d vectors); `IngestResult.status == ok`
- [ ] Entities from mock extractor persisted in graph store â€” verified via `GraphStore.list_entities()`
- [ ] Edges from mock extractor persisted in graph store â€” verified via `GraphStore.list_edges()`
- [ ] Chunk embeddings stored in vector store â€” verified via `VectorStoreProtocol.search_similar()` returning the ingested chunk IDs
- [ ] `KnowledgeQueryService.query()` returns non-empty `list[StructuredSearchResult]` containing the ingested document
- [ ] `GraphAugmentedRetriever.retrieve()` returns `RetrievalResult` with `entities_found > 0` and non-empty `expansion_text` (graph expansion from test entities with edges)
- [ ] All storage uses in-memory Qdrant (`location=:memory:`) and in-memory SQLite (`:memory:`) â€” no Docker, no filesystem deps
- [ ] Test file: `tests/test_knowledge_integration.py`; single class-scoped fixture ingests once, individual tests assert different aspects
- [ ] Module-level `pytest.skip` when `qdrant-client` is not installed (follow pattern from `packages/knowledge/tests/test_qdrant_vector_store.py`)
- [ ] `ruff check` clean on the test file

## Context
Split from #34 per docs/research/knowledge-package-integration-hybrid-search.md. Depends on #158 (IngestPipeline with full persistence â€” done) and #34 (GraphAugmentedRetriever + query_for_context). See docs/research/integration-test-ingest-to-search-cycle.md for full test strategy.

### Test strategy
- Mock StructuredExtractor returning deterministic entities and edges
- Mock EmbeddingProvider returning deterministic 1024-d dense vectors (same vector for all texts ensures cosine similarity = 1.0)
- Real TextChunker, IngestPipeline, DocumentStore, GraphStore, QdrantVectorStore, KnowledgeQueryService, GraphAugmentedRetriever
- Class-scoped fixture performs ingest once; individual test methods assert each AC line

[[2026-03-30]] Mon 23:03
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| IngestPipeline.ingest() with mock extractor/embedder | Precise: method, mocks, expected status specified | Tightened from original |
| Entities persisted via GraphStore.list_entities() | Verifiable assertion | Tightened |
| Edges persisted via GraphStore.list_edges() | Verifiable assertion | Tightened |
| Chunk embeddings via search_similar() | Verifiable: search returns ingested chunk IDs | Tightened |
| KnowledgeQueryService.query() returns results | Specifies non-empty StructuredSearchResult list | Tightened |
| GraphAugmentedRetriever.retrieve() with expansion | Specifies entities_found > 0 and non-empty expansion_text | Tightened |
| In-memory Qdrant + SQLite | Clear constraint, no external deps | Kept |
| Test file location | tests/test_knowledge_integration.py | Added |
| qdrant-client skip pattern | Follows established pattern in test_qdrant_vector_store.py | Added |
| ruff clean | Standard gate | Added |

### Architecture Notes
- All interfaces under test exist: IngestPipeline (ingest.py), DocumentStore (document_store.py), GraphStore (graph_store.py), KnowledgeQueryService (query_service.py), GraphAugmentedRetriever (retrieval.py), QdrantVectorStore (qdrant.py)
- GraphAugmentedRetriever and query_for_context are NOT yet exported from __init__.py (delivered by #34). Test must import directly from retrieval module
- Mocking strategy sound: mock only non-deterministic parts (extractor, embedder), real for everything else. Using same deterministic vector for all texts gives cosine sim = 1.0 ensuring search hits
- #206 tested ingest storage path only (59 tests, archived). #162 extends to full retrieval/query path. No duplication
- qdrant-client graceful skip pattern established in test_qdrant_vector_store.py (pytest.skip at module level)

### Changes Made
- Rewrote AC: 10 precise verifiable lines (was 7 with some vagueness)
- Added mock strategy specs (deterministic extractor, deterministic 1024-d vectors)
- Added assertion methods (list_entities, list_edges, search_similar, query, retrieve)
- Added test file location and qdrant skip pattern AC
- Added ruff clean requirement
- Preserved test strategy section from research

### Dependencies
- Verified: #158 (intake/ingest pipeline) at done
- Verified: #34 (hybrid search + retrieval) at todo, delivers GraphAugmentedRetriever exports and query_for_context on KnowledgeQueryService. Dependency correct
- No TDD pair needed: this IS the test task (type:test)
