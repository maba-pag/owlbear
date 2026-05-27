---
id: 1904
title: 'Knowledge: Implement SourceFetcher adapter and migrate refresh to IngestCoordinator
  (Phase B2b)'
status: research
priority: needed
created: 2026-05-27T23:24:10.601235+02:00
updated: 2026-05-27T23:24:10.601235+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1900
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Create a SourceFetcher implementation that wraps existing fetch logic (URL_LIST, FILE_GLOB, AUTHENTICATED_WEB handlers from RefreshOrchestrator) and wire it into IngestCoordinator. Replace `knowledge_sources_refresh` to use `ingest_coordinator.refresh(RefreshRequest)`.

## Context
- `SourceFetcher` protocol defined in `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` — zero implementations exist
- `IngestCoordinator.refresh()` requires a `SourceFetcher` passed at construction (or set later)
- `RefreshOrchestrator` in `serve/knowledge/src/owlbear_knowledge/refresh.py` has ~200 LOC of source-type-specific fetch logic
- Research: .owlbear/research/mcp-knowledge-legacy-removal-b2.md §3.3

## Changes required
- Create concrete SourceFetcher implementation (adapter wrapping intake.read_url, file glob, and authenticated web fetch)
- Pass fetcher to IngestCoordinator in MCP server lifespan
- Replace `knowledge_sources_refresh` to call `ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))`
- Validate source exists and is ACTIVE via `source_store_v2.get_source()` before calling refresh
- Remove `source_store` (old) and `refresh_orchestrator` from AppContext after migration
- Remove remaining legacy imports (KnowledgeSourceStore, RefreshOrchestrator, IngestPipeline)

## Verification
- knowledge_sources_refresh works via IngestCoordinator path
- All MCP knowledge tests pass
- No remaining legacy imports in mcp-knowledge server.py