---
id: 1897
title: 'Knowledge: MCP server v2-only migration (Phase B)'
status: research
priority: needed
created: 2026-05-27T16:19:48.281533+02:00
updated: 2026-05-27T16:19:48.281533+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1896
ac:
  - AppContext contains only new v2 store fields
  - _consolidation.py deleted; logic migrated to EnrichmentStore
  - No dual-path legacy fallbacks remain in MCP tools
  - All MCP knowledge tests pass
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Remove all legacy components from MCP server AppContext. Wire all tools exclusively to new protocol stores.

## Changes required
- Remove AppContext fields: query_service, graph_store (old), ingest_pipeline, source_store (old), refresh_orchestrator, intra_doc_builder
- Remove dual-path in search_knowledge (delete query_service fallback)
- Migrate _consolidation.py logic into EnrichmentStore (phase-2 candidates)
- Remove init_db() call to old schema.py; new stores use ensure_tables()
- Update all MCP tool functions to use only v2 store APIs
- Delete _consolidation.py after migration

## Verification
- Full MCP test suite passes
- search_knowledge works without query_service
- store_enrichment phase-2 works via EnrichmentStore
- No imports from legacy knowledge modules remain in mcp-knowledge package

## Research
See .owlbear/research/knowledge-legacy-deletion.md §3.3, §3.1