---
id: 162
title: 'Integration test: full ingest-to-search cycle'
status: backlog
priority: needed
created: 2026-03-29T19:37:50.9697847+02:00
updated: 2026-03-30T08:33:21.132249+02:00
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
- [ ] Test ingests a text document through IngestPipeline
- [ ] Entities extracted and stored in graph store
- [ ] Graph edges built (intra-document)
- [ ] Chunks embedded and stored in Qdrant
- [ ] Query via KnowledgeQueryService returns relevant results
- [ ] Query via GraphAugmentedRetriever includes graph expansion context
- [ ] Test runs with in-memory Qdrant and SQLite (no external deps)

## Context
Split from #34 per docs/research/knowledge-package-integration-hybrid-search.md. Blocked on #33 (IngestPipeline extraction) and #161 (package verification). This was originally a #34 AC item but requires the ingest pipeline that #33 delivers.

[[2026-03-30]] Mon 08:32
## Research

### Key Finding: Dependency Gap
Current IngestPipeline (ingest.py) does NOT persist entities, edges, or embeddings to stores. It only chunks text, inserts document record, and counts extraction results. Task #158 delivers the upgraded pipeline with full persistence (store_extractions, store_embeddings).

### Dependency Update
Changed from `depends_on: [33, 161]` to `depends_on: [158, 34]`:
- #158 (intake/ingest pipeline upgrade) delivers IngestPipeline that persists entities+edges+embeddings. Transitively depends on #33 (real entity extraction).
- #34 (hybrid search + retrieval) delivers GraphAugmentedRetriever for AC item 6. Transitively covers #159.
- #161 (README/installability) removed: docs gate, not a code dependency.

### Test Strategy (.90 confidence)
- In-memory SQLite + Qdrant (no external deps)
- Mock StructuredExtractor returning deterministic entities/edges
- Mock EmbeddingProvider returning deterministic 1024-d vectors
- Real TextChunker, IngestPipeline, KnowledgeQueryService, GraphAugmentedRetriever
- Place in tests/test_knowledge_integration.py (root test dir, not package tests)
- Single class-scoped fixture ingests once, individual tests assert different aspects

### Overlap with #206
#206 has partial E2E (ingest storage only). #162 extends to full retrieval path. No duplication.

Research doc: docs/research/integration-test-ingest-to-search-cycle.md
