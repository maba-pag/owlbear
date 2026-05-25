---
id: 1883
title: 'Knowledge: Legacy code deletion'
status: research
priority: needed
created: 2026-05-25T19:05:51.888164+02:00
updated: 2026-05-25T19:05:51.888164+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1881
  - 1882
ac:
  - 'Removed files: source_store.py, document_store.py, graph_store.py, graph_builder.py,
    status_store.py, old ingest.py, query_service.py, retrieval.py, refresh.py, old
    protocol.py, old models.py, old schema.py, MCP helpers (_enrichment.py, _consolidation.py)'
  - No remaining imports of deleted modules anywhere in the codebase
  - All tests pass after deletion (no test depends on legacy code)
  - Old table DDL removed; only new store-owned schema remains
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Remove all unused legacy implementation files. Clean sweep after all MCP tools are wired to new protocol-conformant implementations.

## Context

- Depends on: All MCP tools wired and proven (#1881, #1882)
- Legacy files to remove from `serve/knowledge/src/owlbear_knowledge/`:
  - `source_store.py` (replaced by stores/sources.py)
  - `document_store.py` (replaced by stores/content.py)
  - `graph_store.py` (replaced by stores/graph.py)
  - `graph_builder.py` (subsumed by EnrichmentStore suggest_intra_doc_edges)
  - `status_store.py` (subsumed by ContentStore dedup)
  - `ingest.py` (old pipeline, replaced by ingest_coordinator.py)
  - `query_service.py` (replaced by query_facade.py)
  - `retrieval.py` (subsumed by QueryFacade.search)
  - `refresh.py` (subsumed by IngestCoordinator.refresh)
  - `protocol.py` (old VectorStoreProtocol etc, replaced by protocols/)
  - `models.py` (old data models, replaced by protocol types)
  - `schema.py` (old monolithic DDL, replaced by per-store ensure_tables)
- Legacy MCP helpers to remove from `serve/mcp-knowledge/`:
  - `_enrichment.py`, `_consolidation.py`

## Implementation Notes

- grep for all imports of deleted modules; fix or remove
- Old tests that only test legacy code can be removed
- Verify: `uv run python -c \"import owlbear_knowledge\"` passes
- Verify: full test suite passes