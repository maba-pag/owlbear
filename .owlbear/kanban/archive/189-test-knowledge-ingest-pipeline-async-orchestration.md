---
id: 189
title: Test knowledge ingest pipeline — async orchestration
status: archived
priority: needed
created: 2026-02-27T22:17:49.8440295+01:00
updated: 2026-02-28T23:53:38.5917248+01:00
started: 2026-02-28T00:26:36.8402928+01:00
completed: 2026-02-28T23:53:38.5917248+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

Write tests in tests/test_knowledge_ingest.py for src/owlbear/memory/knowledge/ingest.py. Test: (1) IngestPipeline accepts GraphStore, VectorStore, EmbeddingProvider, EntityExtractor, TextChunker (2) ingest() orchestrates intake->chunk->parallel(embed, extract)->store (3) IngestResult model has document_id, chunk_count, entity_count, edge_count, status fields (4) Document status transitions: pending->processing->indexed on success (5) Document status transitions: pending->processing->failed on error (6) Error in extract logs warning but embed+store still completes (partial success) (7) Error in embed logs warning but extract+store still completes (8) All external deps mocked (EmbeddingProvider, EntityExtractor, GraphStore, VectorStore) (9) Uses pytest-asyncio for async tests
