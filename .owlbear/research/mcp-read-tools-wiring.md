# Knowledge MCP Read Tools — Wiring to Protocol Implementations

> **Owning task:** #1881 — Knowledge: MCP tools — read operations
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

How should the MCP knowledge server's 4 read tools be rewired from legacy implementations to the new protocol-conformant stores (QueryFacade, SqliteSourceStore, SqliteGraphStore, IngestCoordinator)?

The `MCP_TOOL_ROUTING` registry in `protocols/registry.py` defines the target architecture:

| MCP Tool Name | Target Method | Current Function |
|---|---|---|
| `knowledge_search` | `QueryFacade.search` | `search_knowledge` (uses legacy `KnowledgeQueryService`) |
| `knowledge_sources_list` | `SourceStore.list_sources` | `list_sources` (uses legacy `KnowledgeSourceStore`) |
| `knowledge_entity_lookup` | `QueryFacade.lookup_entity` | `list_entities` (deferred/internal, uses legacy `GraphStore.list_entities`) |
| `knowledge_stats` | `IngestCoordinator.stats` | `get_stats` (raw SQL on legacy schema) |

## 2. Sources Studied

| Source | Type | Relevance |
|---|---|---|
| `protocols/registry.py` MCP_TOOL_ROUTING | Codebase | 1.0 — defines the contractual tool→method mapping |
| `protocols/query.py` QueryFacade protocol | Codebase | 1.0 — defines request/result shapes for search + lookup |
| `protocols/sources.py` SourceStore protocol | Codebase | 0.9 — defines list_sources contract |
| `protocols/ingest.py` IngestStats model | Codebase | 0.9 — defines stats() response shape |
| `query_facade.py` implementation | Codebase | 1.0 — working impl, wires Content+Graph |
| `stores/graph.py` SqliteGraphStore | Codebase | 0.9 — protocol-conformant graph store with find_entities, stats |
| `ingest_coordinator.py` stats() | Codebase | 1.0 — aggregates from all leaf stores |
| `server.py` current tool implementations | Codebase | 1.0 — the code to be replaced |

## 3. Analysis

### 3.1 Dependency Graph (instantiation order)

```
SqliteGraphStore(conn)              # new — must replace legacy GraphStore
  └── ContentStore(db, vs, emb, chunker)   # already exists
  └── EnrichmentStore(db, graph)           # already exists, needs SqliteGraphStore
  └── IngestCoordinator(sources, content, enrichment, graph)  # already exists
QueryFacade(content, graph)          # new — needs ContentStore + SqliteGraphStore
```

### 3.2 Key Findings

**F1: Schema split.** Legacy `GraphStore` uses `entities`/`edges` tables. New `SqliteGraphStore` uses `graph_entities`/`graph_edges`/`graph_evidence`/`graph_aliases` (per `TABLE_OWNERSHIP`). The two operate on different tables. `SqliteGraphStore.ensure_tables()` must be called at startup (currently omitted).

**F2: Legacy GraphStore still needed.** The legacy `GraphStore` is consumed by `GraphAugmentedRetriever`, `KnowledgeQueryService`, `DocumentStore`, `IngestPipeline`, and `IntraDocGraphBuilder` — all of which support the current `search_knowledge` tool. During the transition, both stores coexist. Only the 4 read tools targeted by #1881 need to switch.

**F3: QueryFacade not instantiated.** The MCP server lifespan does not create a `QueryFacade`. It needs `content: ContentStore` (already available as `content_store`) and `graph: GraphStore` protocol (needs `SqliteGraphStore`).

**F4: Response shape changes.** The protocol returns Pydantic models (`QueryResult`, `EntityLookupResult`, `IngestStats`) which differ from current `TypedDict` shapes (`SearchResult`, `EntityInfo`, `StatsResult`). The MCP tool layer must serialize protocol models into the existing MCP response shapes (or define new ones with clear documentation of the breaking change).

**F5: Error mapping.** Protocol raises `ValueError` (invalid input) and `LookupError` (entity not found). MCP layer must catch and convert to `ToolError` (already the pattern used elsewhere in the server).

**F6: Tool renaming.** Current exposed tool names (`search_knowledge`, `list_sources`, `get_stats`) don't match `MCP_TOOL_ROUTING` names (`knowledge_search`, `knowledge_sources_list`, `knowledge_stats`). Renaming tools is a breaking change for all MCP consumers — agents have the old names in their tool lists.

### 3.3 Trade-Off Matrix: Rename vs Alias

| Criteria | Rename (break) | Alias (both names) | Keep old names |
|---|---|---|---|
| Registry compliance | ✅ matches `MCP_TOOL_ROUTING` | ✅ both work | ❌ diverges |
| Consumer disruption | ❌ all agents break | ⚠️ needs exclusion-env coordination | ✅ none |
| Complexity | Low | Medium (duplicate registration) | Low |
| KISS alignment | ✅ | ⚠️ | ⚠️ registry lies |
| Confidence | .70 | .55 | .60 |

### 3.4 Trade-Off Matrix: Response Shape

| Criteria | Serialize to existing TypedDicts | Return raw model.model_dump() | New TypedDicts from protocol |
|---|---|---|---|
| Backwards compat | ✅ no consumer breakage | ❌ field names differ | ❌ new fields |
| Fidelity | ⚠️ loses protocol data | ✅ full data | ✅ full data |
| Maintenance | ⚠️ mapping code needed | ✅ minimal | ⚠️ parallel types |
| Confidence | .75 | .65 | .60 |

## 4. Recommendation

**Approach: Incremental migration with old→new shim (confidence: .80)**

1. **Add `SqliteGraphStore` to lifespan** — instantiate, call `ensure_tables()`, add to `AppContext` as a new field (`graph_store_v2`).
2. **Add `QueryFacade` to lifespan** — instantiate with `content_store` + `graph_store_v2`, add to `AppContext` as `query_facade`.
3. **Rewire read tools one at a time**, keeping the old function names but delegating to protocol methods internally. This avoids consumer breakage while complying with the "tools delegate to protocol methods" principle from the registry doc.
4. **Response serialization** — map protocol models back to existing `TypedDict` shapes where feasible. Document what data is newly available. The `knowledge_entity_lookup` tool is new (replacing deferred `list_entities`), so its shape can follow the protocol directly.
5. **Tool renaming deferred** — flag as separate follow-up task (T2, advisory). Rename requires coordinated agent config update.

Challenge: proceed — confidence in original: .80. The incremental approach minimizes blast radius while achieving the core goal (protocol delegation).

## 5. Follow-up Tasks

1. **Wire read tools to protocol stores** — Actual implementation task (todo status): add `SqliteGraphStore` + `QueryFacade` to lifespan, rewire `search_knowledge` → `QueryFacade.search`, `list_sources` → `SqliteSourceStore.list_sources`, expose `knowledge_entity_lookup` → `QueryFacade.lookup_entity`, rewire `get_stats` → `IngestCoordinator.stats`.
2. **Tool rename coordination** (advisory, T2) — Rename exposed MCP tool names to match `MCP_TOOL_ROUTING` registry (`knowledge_search`, `knowledge_sources_list`, `knowledge_entity_lookup`, `knowledge_stats`). Requires updating all agent tool-allowlists.
3. **Remove legacy graph dependencies** (future) — Once all tools use `SqliteGraphStore`, remove `GraphStore` (legacy), `GraphAugmentedRetriever`, `KnowledgeQueryService`, and related imports. Blocked by write-tool migration (#1882+).
