---
id: 1911
title: 'Knowledge: Wire SourceFetcher in MCP server and replace refresh handler'
status: backlog
priority: needed
created: 2026-05-28T01:41:45.877792+02:00
updated: 2026-05-28T01:41:51.228330+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent: 1904
depends_on:
  - 1909
  - 1910
ac:
  - 'AC1: knowledge_sources_refresh returns success result via IngestCoordinator path'
  - 'AC2: AppContext has no refresh_orchestrator or source_store fields'
  - 'AC3: No remaining legacy imports (KnowledgeSourceStore, RefreshOrchestrator,
    IngestPipeline) in server.py'
  - 'AC4: Handler validates source exists and is ACTIVE before calling refresh'
  - 'AC5: All existing MCP knowledge tests pass'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Wire CompositeSourceFetcher in the MCP server lifespan and replace the refresh handler to use IngestCoordinator.

## Details
- In `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` app_lifespan:
  - Create CompositeSourceFetcher(workspace_root=Path.cwd(), content_fetcher_factory=select_content_fetcher)
  - Pass fetcher= to IngestCoordinator constructor
- Replace knowledge_sources_refresh handler body:
  - Validate source exists via source_store_v2.get_source(source_id), raise ToolError if not found
  - Check source.state is ACTIVE, return error if not
  - Call ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))
  - Map RefreshResult to response dict
- Remove refresh_orchestrator and source_store fields from AppContext
- Remove legacy imports (KnowledgeSourceStore, RefreshOrchestrator, IngestPipeline, select_content_fetcher usage in handler)
- Depends on: #1909 (CompositeSourceFetcher) and #1910 (error propagation)
- Research: .owlbear/research/source-fetcher-adapter-b2b.md §3.4