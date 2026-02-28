---
id: 176
title: Knowledge ingest pipeline — async orchestrator
status: archived
priority: needed
created: 2026-02-27T22:10:08.0563632+01:00
updated: 2026-02-28T23:53:25.5876477+01:00
started: 2026-02-27T22:12:00.7519441+01:00
completed: 2026-02-28T23:53:25.5876477+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 173
    - 174
    - 175
    - 177
    - 189
class: standard
---

Module: src/owlbear/memory/knowledge/ingest.py | Test: tests/test_knowledge_ingest.py | See docs/knowledge-ingestion-research.md S3.4.

AC:
- IngestPipeline class accepting GraphStore, VectorStore, EmbeddingProvider, EntityExtractor, TextChunker
- async ingest(source: str | Path) -> IngestResult — orchestrates: intake -> chunk -> parallel(embed, extract) -> store
- IngestResult frozen Pydantic model: document_id: str, chunk_count: int, entity_count: int, edge_count: int, status: str
- Embed and extract run in parallel via asyncio.gather (embed is CPU-bound, extract is LLM I/O-bound)
- Document status tracking in document_status table: pending -> processing -> indexed (success) or failed (error)
- Error in extract step: logs WARNING, embed+store still completes (partial success, status='partial')
- Error in embed step: logs WARNING, extract+store still completes (partial success, status='partial')
- Failed documents can be retried by calling ingest() again (checks document_status)
- Stores chunks in chunks table, entities/edges in GraphStore, embeddings in VectorStore
- ruff clean, all tests in tests/test_knowledge_ingest.py pass
