---
id: 1894
title: 'Knowledge: wire MCP read tools to protocol stores'
status: research
priority: needed
created: 2026-05-27T11:05:26.124244+02:00
updated: 2026-05-27T11:05:26.124244+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1881
ac:
  - search_knowledge delegates to QueryFacade.search; response matches current 
    SearchResult TypedDict
  - list_sources delegates to SqliteSourceStore.list_sources; filters by scope 
    and state
  - knowledge_entity_lookup tool exposed, delegates to QueryFacade.lookup_entity
  - get_stats delegates to IngestCoordinator.stats; response includes sources, 
    documents, chunks, graph counts
  - SqliteGraphStore.ensure_tables() called at startup
  - All error paths (ValueError, LookupError) mapped to ToolError
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Wire the 4 MCP read tools (search_knowledge, list_sources, knowledge_entity_lookup, get_stats) to protocol-conformant implementations.

## Implementation Steps

- Add SqliteGraphStore to lifespan (instantiate, ensure_tables(), add as graph_store_v2 in AppContext)
- Add QueryFacade to lifespan (content_store + graph_store_v2, add as query_facade in AppContext)
- Rewire search_knowledge → QueryFacade.search (map QueryResult back to SearchResult TypedDict)
- Rewire list_sources → SqliteSourceStore.list_sources (map SourceRecord to SourceInfo TypedDict)
- Add knowledge_entity_lookup tool → QueryFacade.lookup_entity (new tool, protocol model shapes ok)
- Rewire get_stats → IngestCoordinator.stats (map IngestStats to StatsResult TypedDict)
- Error mapping: ValueError → ToolError, LookupError → ToolError

## Context

Depends on all layer-1/2 tasks (already completed). See .owlbear/research/mcp-read-tools-wiring.md