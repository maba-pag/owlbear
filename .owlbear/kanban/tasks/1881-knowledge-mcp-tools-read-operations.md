---
id: 1881
title: 'Knowledge: MCP tools — read operations'
status: review
priority: needed
created: 2026-05-25T19:05:23.030124+02:00
updated: 2026-05-27T12:14:10.590779+02:00
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

[[2026-05-27T11:54:11+02:00]]
## Test-Writer Notes
- Test file: tests/test_mcp_knowledge_read_tools_1881.py
- Classes: TestFromAC_AppContextFieldsV2, TestFromAC_SearchKnowledgeDelegate, TestFromAC_ListSourcesDelegate, TestFromAC_EntityLookupTool, TestFromAC_GetStatsDelegation, TestFromAC_ErrorHandling
- Tests per category: happy 10, edge 8, error 11, boundary 7
- Total: 36 tests, all FAIL
- ruff: clean

AC coverage table:
| AC | Tests | Failure evidence |
|----|-------|-----------------|
| AC1 — AppContext query_facade+graph_store_v2+lifespan | 7 | AttributeError: 'AppContext' object has no attribute 'query_facade'/'graph_store_v2'; ensure_tables not called |
| AC2 — search_knowledge → QueryFacade.search | 5 | AssertionError: expected list (query_service returns error string); query_service.query called when it shouldn't be |
| AC3 — list_sources → SqliteSourceStore.list_sources | 5 | AssertionError: store_v2.list_sources not called; legacy list_all still called; DID NOT RAISE ToolError |
| AC4 — knowledge_entity_lookup new tool | 8 | ImportError: cannot import name 'knowledge_entity_lookup' from server |
| AC5 — get_stats → IngestCoordinator.stats() | 6 | AssertionError: coordinator.stats not called; total_sources=0 not 99; entities=11 not 77; chunks_pending=0 not 13 |
| AC6 — Error handling ValueError/LookupError/ValidationError → ToolError | 5 | ImportError (entity_lookup); assert ToolError not raised for ValueError |

[[2026-05-27T12:14:10+02:00]]
## Builder Notes
- Implementation: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- AC1: Added `query_facade` + `graph_store_v2` to `AppContext`; wired `SqliteGraphStore` and `QueryFacade` in lifespan; call `graph_store_v2.ensure_tables()` at startup; retained legacy `graph_store` for existing non-read paths.
- AC2: Rewired `search_knowledge` to use `QueryFacade.search(QueryRequest(...))` with protocol request construction and `ValueError -> ToolError` mapping. Added a strict legacy-context compatibility branch (only when `query_facade` field is absent) to avoid unrelated regression in durable tests.
- AC3: Rewired `list_sources` to `SqliteSourceStore.list_sources(scope=scope)` and mapped response to `SourceInfo` shape (`source_type` from `kind`), with guard `source_store_v2` required.
- AC4: Added MCP tool `knowledge_entity_lookup` with params `entity_id`, `entity_name`, `entity_type`, `expand_hops=1`; delegates to `QueryFacade.lookup_entity(EntityLookupRequest)` and serializes entity/neighbourhood/related_chunks.
- AC5: Rewired `get_stats` to `IngestCoordinator.stats()` (base counts) + `EnrichmentStore.stats()` (pending/in_progress/failed/completed) while preserving `StatsResult` keys and SQL-derived claimable/consolidation fields.
- AC6: Error mapping implemented: `ValueError`, `LookupError`, `ValidationError` -> `ToolError` for read-tool protocol boundaries.

- Test verification (quality-runner):
  - `tests/test_mcp_knowledge_read_tools_1881.py`: 36 passed, 0 failed
  - Durable module-level check `tests/test_search_provenance.py`: 28 passed, 0 failed
  - Combined scoped regression (`tests/test_mcp_knowledge_read_tools_1881.py`, `tests/test_search_provenance.py`): 64 passed, 0 failed
- Lint (quality-runner): clean (`ruff` clean for source + task tests)
- Coverage (quality-runner): `owlbear_mcp_knowledge.server` 41% in scoped run (task + durable module-level tests)
- Commit: a3447430 (`feat: wire MCP knowledge read tools to protocol stores (#1881, builder)`)

Evidence summary: behavioral AC implemented with protocol-conformant wiring, task tests green, and durable search-provenance regression check green after compatibility-safe legacy-context fallback.
