---
id: 1881
title: 'Knowledge: MCP tools — read operations'
status: todo
priority: needed
created: 2026-05-25T19:05:23.030124+02:00
updated: 2026-05-27T11:36:17.298427+02:00
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
  - SqliteGraphStore + QueryFacade added to AppContext and instantiated in 
    lifespan; SqliteGraphStore.ensure_tables() called at startup; legacy 
    graph_store retained for non-read tools
  - search_knowledge delegates to QueryFacade.search(QueryRequest(text=query, 
    top_k=limit, scopes=scopes)); response mapped to existing SearchResult 
    TypedDict via serialization helpers
  - list_sources delegates to SqliteSourceStore.list_sources(scope=scope); 
    response mapped to existing SourceInfo TypedDict; state parameter NOT 
    exposed as MCP param (deferred to follow-up)
  - 'knowledge_entity_lookup tool registered with @mcp.tool; params: entity_id: str|None,
    entity_name: str|None, entity_type: str|None, expand_hops: int=1; delegates to
    QueryFacade.lookup_entity(EntityLookupRequest); returns serialized entity + neighbourhood'
  - get_stats delegates to IngestCoordinator.stats() for base counts 
    (sources_total, documents_total, chunks_total, graph_entities, graph_edges);
    enrichment detail fields 
    (chunks_pending/claimed/failed/enriched/claimable/ratio) computed from 
    EnrichmentStore; consolidation_candidates_remaining from existing SQL; 
    StatsResult TypedDict shape preserved
  - 'Error handling: ValueError raises ToolError, LookupError raises ToolError, Pydantic
    ValidationError raises ToolError; no raw exception strings in MCP responses'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-27T11:36:17.298427+02:00
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

[[2026-05-27T11:06:14+02:00]]
## Research

Key findings:
- 4 read tools need rewiring: search_knowledge → QueryFacade.search, list_sources → SqliteSourceStore.list_sources, knowledge_entity_lookup (new) → QueryFacade.lookup_entity, get_stats → IngestCoordinator.stats
- QueryFacade and SqliteGraphStore not yet instantiated in MCP server lifespan
- Legacy GraphStore uses different schema (entities/edges) vs protocol store (graph_entities/graph_edges) — both coexist during transition
- Response shape strategy: map protocol models back to existing TypedDicts to avoid consumer breakage
- Tool rename is a separate concern (breaking change for agents) — deferred to follow-up

Trade-off: incremental migration with protocol delegation behind existing tool names (confidence .80)

Doc: .owlbear/research/mcp-read-tools-wiring.md
Follow-ups: #1894 (wire read tools), #1895 (rename tools to match registry)

[[2026-05-27T11:35:41+02:00]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 4 read tools wired to protocol stores — one logical concern |
| Interface clarity | PASS (after refine) | AC specifies exact delegation targets, parameter shapes, response TypedDicts |
| Dependency correctness | PASS | All 6 deps archived; #1894 is a duplicate (recommend archival) |
| Module layering | PASS | MCP server → protocol implementations (downward) |
| TDD compliance | PASS | Behavioral bundle — tests required |
| KISS/YAGNI | PASS | Straightforward delegation wiring with minimal mapping |
| Premise challenge | PASS | Rewiring mandated by protocol architecture migration |
| Pattern consistency | PASS | Follows existing ToolError patterns, AppContext, asyncio.to_thread |
| Security surface | PASS | Read-only operations, no new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| QueryFacade.search | empty text | ValueError | Yes → ToolError | MCP error |
| QueryFacade.lookup_entity | entity not found | LookupError | Yes → ToolError | MCP error |
| EntityLookupRequest validation | both/neither id+name | ValidationError | Yes → ToolError | MCP error |
| SqliteGraphStore.ensure_tables | DB locked at startup | sqlite3.OperationalError | Propagates (startup crash) | Server won't start |
| IngestCoordinator.stats | Never raises (documented) | N/A | N/A | N/A |

### Design Diverge
- Trigger: skipped — single valid approach (incremental migration behind existing tool names per research)

### Challenge Results
- Challenger: reconsider (confidence 0.44)
- Findings: registry contract conflict, dual-store ambiguity, stats field mismatch, parameter gaps
- Architect response: REVISED — rebutted registry interpretation (routing ≠ serialization); accepted dual-store clarity, stats hybrid approach, parameter specificity, and error completeness into refined AC

### Proof-Bundle Validation
- Planner assignment: null (no prior assignment)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Notes
- #1894 (research) is a duplicate of this task — recommend archival with \"merged into #1881\"
- #1895 depends on #1894; should be updated to depend on #1881 instead
- Legacy stores (GraphStore, KnowledgeQueryService, KnowledgeSourceStore) remain active for write tools and enrichment — only read tools switch to protocol stores
- Tool renaming deferred to #1895

### Verdict: APPROVE
### Action Taken: AC refined from challenger feedback (6 precise criteria replacing 5 vague ones); proof_bundle set to behavioral; advanced to todo

[[2026-05-27T11:35:48+02:00]]
Architecture review complete. AC refined from 5 vague criteria to 6 precise testable criteria based on challenger feedback. Key refinements: explicit dual-store coexistence scope, hybrid stats approach (coordinator + EnrichmentStore), parameter shapes for new entity_lookup tool, complete error taxonomy. Proof bundle: behavioral. Note: #1894 is a duplicate — recommend archival with \"merged into #1881\"; update #1895 dep from #1894 → #1881.
