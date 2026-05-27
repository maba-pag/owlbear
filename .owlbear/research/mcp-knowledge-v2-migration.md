# Knowledge: MCP Server v2-Only Migration (Phase B)

> **Owning task:** #1897 — Knowledge: MCP server v2-only migration (Phase B)
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Can the MCP knowledge server be migrated to use exclusively v2 store APIs, removing all legacy AppContext fields and dual-path logic? What's the work breakdown, risks, and sequencing?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (1315 LOC) | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_consolidation.py` (539 LOC) | Codebase | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` — EnrichmentStore | Codebase | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/stores/graph.py` — SqliteGraphStore | Codebase | 0.9 |
| `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` — refresh/ingest | Codebase | 0.9 |
| `serve/knowledge/src/owlbear_knowledge/protocols/graph.py` — GraphStore Protocol | Codebase | 0.8 |
| `.owlbear/research/knowledge-legacy-deletion.md` (Phase A research) | Prior research | 0.9 |

## 3. Analysis

### 3.1 Legacy fields and their v2 replacements

| Legacy field | Used by | v2 replacement | Migration complexity |
|---|---|---|---|
| `query_service` | `search_knowledge` fallback | `query_facade` (already primary) | Low — delete fallback branch |
| `graph_store` (old GraphStore) | `list_entities`, stats functions, `_knowledge_stats_bridge` | `graph_store_v2.stats()` + `graph_store_v2.find_entities()` | Low |
| `ingest_pipeline` | `refresh_source` | `ingest_coordinator.refresh()` | Medium — different API shape |
| `source_store` (old) | `refresh_source` | `source_store_v2.get_source()` | Low |
| `refresh_orchestrator` | `refresh_source` | `ingest_coordinator.refresh(RefreshRequest)` | Medium |
| `intra_doc_builder` | **None** (dead field) | Remove | Trivial |
| `structured_extractor` | Only wires dead `intra_doc_builder` | Remove | Trivial |

### 3.2 Tool-by-tool migration

| Tool | Current state | Migration action |
|---|---|---|
| `search_knowledge` | Dual-path: tries `query_facade`, falls back to `query_service` | Delete fallback branch + `_serialize_legacy_search_results()` |
| `list_entities` | Uses old `GraphStore.list_entities()` + old `EntityType` enum | **Not exposed as MCP tool** (deferred). Delete entirely. |
| `knowledge_stats` / `_knowledge_stats_bridge` / `knowledge_stats_resource` | Use old `graph_store.get_counts()` | Replace with `graph_store_v2.stats()` + `ingest_coordinator.stats()` |
| `refresh_source` | Uses old `source_store`, `ingest_pipeline`, `RefreshOrchestrator` | Replace with `ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))` |
| `get_consolidation_candidates` | Calls `_consolidation._fetch_consolidation_candidate_rows()` | Call `enrichment_store.get_consolidation_candidates()` after migration |
| `store_enrichment` (phase-2 branch) | Calls `_consolidation._persist_phase2_enrichment()` | Call `enrichment_store.submit_consolidation()` after migration |
| `get_stats` | Calls `_consolidation._count_consolidation_candidates()` | Call `enrichment_store.count_consolidation_candidates()` |

### 3.3 Consolidation migration into EnrichmentStore

**What moves:**
- `_fetch_consolidation_candidate_rows()` → `EnrichmentStore.get_consolidation_candidates(limit)` (~100 LOC SQL CTE)
- `_count_consolidation_candidates()` → `EnrichmentStore.count_consolidation_candidates()` (~50 LOC SQL CTE)
- `_persist_phase2_enrichment()` → `EnrichmentStore.submit_consolidation(candidate_id, edges)` (~80 LOC)
- `_encode_candidate_id` / `_decode_candidate_id` → private helpers inside EnrichmentStore
- `_resolve_candidate_identity`, `_validate_active_candidate_sources`, `_candidate_entity_ids` → private helpers
- `_resolve_phase2_edge_endpoints`, `_load_phase2_edge_provenance` → private helpers

**EnrichmentStore changes needed:**
1. Add `reviewed_pairs` table creation to `ensure_tables()` (currently only in legacy `schema.py`)
2. New public methods: `get_consolidation_candidates(limit)`, `count_consolidation_candidates()`, `submit_consolidation(candidate_id, edges, now_iso)`
3. Import `_stable_edge_id`, `_extract_relation`, `_validate_enrichment_edge_payload` from mcp-knowledge `_helpers.py` OR duplicate/move to knowledge package

**Critical dependency:** `_helpers.py` functions (`_stable_edge_id`, `_extract_relation`, `_validate_enrichment_edge_payload`) are in the mcp-knowledge package but needed by EnrichmentStore (in knowledge package). These must move to the knowledge package (e.g., enrichment store internals) to avoid a reverse dependency.

### 3.4 EnrichmentStore graph dependency (non-issue)

`EnrichmentStore` accepts `graph: GraphStore` (Protocol). `SqliteGraphStore` implements this protocol. Switching from `EnrichmentStore(db=conn, graph=old_gs)` to `EnrichmentStore(db=conn, graph=graph_store_v2)` is safe.

### 3.5 `init_db()` removal

Currently: `conn = init_db(path)` calls `_schema_init_db(conn)` which runs legacy DDL. New stores call `ensure_tables()` independently. After adding `reviewed_pairs` to `EnrichmentStore.ensure_tables()`, the old `init_db()` can be replaced with plain `sqlite3.connect(path)` + individual `ensure_tables()` calls.

### 3.6 Import cleanup

After migration, these imports become dead:
- `DocumentStore`, `GraphStore` (old), `IntraDocGraphBuilder`, `IngestPipeline`
- `KnowledgeSourceStore`, `KnowledgeQueryService`, `KnowledgeQueryError`
- `RefreshOrchestrator`, `GraphAugmentedRetriever`, `BgeM3EmbeddingProvider`
- `EntityExtractor`, `EntityType` (from models.py)
- `schema.init_db`, `TextChunker` (only used to build old pipeline)
- Entire `._consolidation` import block

## 4. Recommendation (confidence: 0.85)

**Two sub-phases** within Phase B to reduce blast radius:

| Sub-phase | Scope | Effort |
|---|---|---|
| B1 — Consolidation migration | Move `_consolidation.py` logic into `EnrichmentStore`; update server.py to call new methods; delete `_consolidation.py` | ~200 LOC new, ~540 LOC deleted |
| B2 — Server v2-only | Remove legacy AppContext fields + dual-paths; replace `refresh_source`, stats, search fallback; remove `init_db()` wrapper; clean imports | ~150 LOC deleted, ~30 LOC new |

**Rationale for split:** B1 is self-contained (enrichment module) and testable independently. B2 touches every tool and the lifespan but requires B1 to be done first (otherwise `store_enrichment` phase-2 has no home).

**Risk:** `refresh_source` behavior change. Old `RefreshOrchestrator` has specific per-source refresh semantics. `IngestCoordinator.refresh()` has a different model (batch refresh by source_ids). The tool's return type (`dict` with refreshed/partial/skipped/failed/errors/warnings) may not map cleanly to `RefreshResult`. Needs careful adaptation.

Challenge: N/A — straightforward migration with clear replacement APIs; no contested recommendation.

## 5. Follow-up Tasks

- **B1:** Migrate consolidation logic from `_consolidation.py` into `EnrichmentStore` (move helpers, add `reviewed_pairs` DDL, new public methods)
- **B2:** Remove all legacy AppContext fields, dual-paths, old imports; wire tools to v2 APIs exclusively (depends on B1)
