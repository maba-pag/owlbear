---
id: 1900
title: 'Knowledge: Remove legacy AppContext fields and dual-paths (Phase B2)'
status: research
priority: needed
created: 2026-05-27T17:56:21.002017+02:00
updated: 2026-05-27T18:00:29.762442+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1899
ac:
  - AppContext contains only v2 store fields (no query_service, graph_store, 
    ingest_pipeline, source_store, refresh_orchestrator, intra_doc_builder)
  - search_knowledge has no legacy fallback path
  - refresh_source uses IngestCoordinator.refresh()
  - No imports from legacy knowledge modules (graph_store, query_service, 
    ingest, source_store, refresh, retrieval, schema, models, document_store) in
    mcp-knowledge
  - All MCP knowledge tests pass
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Remove all legacy components from the MCP server AppContext. Wire tools exclusively to v2 store APIs.

## Changes required
- Remove AppContext fields: query_service, graph_store, ingest_pipeline, source_store, refresh_orchestrator, intra_doc_builder, structured_extractor
- Remove dual-path in `search_knowledge` (delete query_service fallback + `_serialize_legacy_search_results()`)
- Replace `refresh_source` to use `ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))`
- Replace stats functions (`knowledge_stats`, `_knowledge_stats_bridge`, `knowledge_stats_resource`) to use `graph_store_v2.stats()` + `ingest_coordinator.stats()`
- Delete `list_entities` function (deferred/unexposed, uses legacy APIs)
- Remove `init_db()` wrapper that calls `_schema_init_db()`; use plain `sqlite3.connect()` + individual `ensure_tables()` calls in lifespan
- Remove all dead legacy imports (DocumentStore, GraphStore, IngestPipeline, KnowledgeSourceStore, KnowledgeQueryService, RefreshOrchestrator, GraphAugmentedRetriever, BgeM3EmbeddingProvider, EntityExtractor, EntityType from models, TextChunker, schema.init_db)
- Wire `EnrichmentStore(db=conn, graph=graph_store_v2)` instead of old GraphStore

## Verification
- Full MCP test suite passes
- search_knowledge works without query_service fallback
- refresh_source works via IngestCoordinator
- Stats functions work via v2 stores
- No imports from legacy knowledge modules remain in mcp-knowledge

## Research
See .owlbear/research/mcp-knowledge-v2-migration.md §3.1, §3.2