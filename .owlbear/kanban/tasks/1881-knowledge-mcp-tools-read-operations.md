---
id: 1881
title: 'Knowledge: MCP tools — read operations'
status: research
priority: needed
created: 2026-05-25T19:05:23.030124+02:00
updated: 2026-05-25T19:05:23.030124+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1870
  - 1873
  - 1874
  - 1877
  - 1879
  - 1880
ac:
  - knowledge_search tool calls QueryFacade.search; response shape matches MCP 
    tool schema
  - knowledge_sources tool calls SourceStore.list_sources with scope/state 
    filters
  - knowledge_entities tool calls GraphStore.find_entities with type/name 
    filters
  - knowledge_stats tool calls IngestCoordinator.stats (aggregates leaf stats)
  - All read tools return proper MCP-format responses; errors propagated via MCP
    error protocol
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Wire MCP server read tools (search, get_sources, get_entities, stats) to the new protocol-conformant implementations.

## Context

- MCP server: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- Tool routing: `protocols/registry.py` MCP_TOOL_ROUTING maps tool names to method paths
- Depends on: QueryFacade (#1879, #1880), SourceStore (#1870), GraphStore (#1873, #1874), IngestCoordinator (#1877)

## Implementation Notes

- MCP server instantiates all stores + coordinators at startup; tools delegate to protocol methods
- Response shapes must match current MCP tool contract (or be upgraded with clear documentation)
- Error mapping: protocol raises (ValueError, LookupError) → MCP error responses
- stats tool aggregates via IngestCoordinator.stats() which calls leaf store stats() methods