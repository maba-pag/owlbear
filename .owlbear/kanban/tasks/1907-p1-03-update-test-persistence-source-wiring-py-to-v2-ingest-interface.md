---
id: 1907
title: 'P1-03: Update test_persistence_source_wiring.py to v2 ingest interface'
status: backlog
priority: needed
created: 2026-05-28T00:34:20.741704+02:00
updated: 2026-05-28T00:34:26.218906+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - test_persistence_source_wiring.py no longer patches GraphStore, init_db, 
    KnowledgeQueryService, GraphAugmentedRetriever, or BgeM3EmbeddingProvider in
    owlbear_mcp_knowledge.server
  - test_persistence_source_wiring.py tests Qdrant persistence and 
    source-identity wiring against v2 lifespan (SqliteGraphStore, 
    IngestCoordinator) or is deleted with supersession justification
  - pytest tests/test_persistence_source_wiring.py passes (0 failures, 0 errors)
    — or file is absent if retired
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Update the durable module-level `tests/test_persistence_source_wiring.py` (~9 tests) to test against the v2 ingest interface, or retire if superseded.

## Current State
- Patches `GraphStore`, `init_db`, `KnowledgeQueryService`, `GraphAugmentedRetriever`, `BgeM3EmbeddingProvider` in `owlbear_mcp_knowledge.server`
- Tests AC1 (Qdrant filesystem persistence), AC4 (source_url parameter), AC6 (source identity by URL)
- Uses `pipeline.ingest_text()` calls which reference removed `IngestPipeline`

## Direction
- Evaluate whether the Qdrant persistence contract and source-identity wiring are now tested by v2-era suites (e.g., `test_ingest_document_coordinator_1893.py` or `serve/mcp-knowledge/tests/`)
- If covered: delete with supersession evidence note
- If not covered: rewrite fixtures to patch v2 lifespan symbols (`SqliteGraphStore`, `QdrantVectorStore`, `IngestCoordinator`) and test the same contracts against `knowledge_ingest` tool

## Scope
- In-scope: rewrite or retire `tests/test_persistence_source_wiring.py`
- Out-of-scope: other test files, server.py changes