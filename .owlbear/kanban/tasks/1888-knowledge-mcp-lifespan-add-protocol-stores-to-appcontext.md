---
id: 1888
title: 'Knowledge: MCP lifespan — add protocol stores to AppContext'
status: research
priority: needed
created: 2026-05-27T01:00:31.607797+02:00
updated: 2026-05-27T01:00:31.607797+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1882
ac:
  - AppContext has content_store, enrichment_store, source_store_v2 
    (SqliteSourceStore), and ingest_coordinator fields
  - Lifespan instantiates all new stores with correct DI (shared sqlite 
    connection, GraphStore, etc.)
  - ensure_tables() called on ContentStore, EnrichmentStore, SqliteSourceStore 
    during startup
  - Existing old store fields remain functional (no breakage of current 
    read/write tools)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Wire new protocol stores (ContentStore, EnrichmentStore, SqliteSourceStore, IngestCoordinator) into the MCP server lifespan. Call ensure_tables() on each. Add fields to AppContext dataclass. Keep existing old stores for backwards compatibility during transition.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`