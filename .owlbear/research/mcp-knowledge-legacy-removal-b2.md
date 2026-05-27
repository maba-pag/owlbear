# Knowledge: Legacy AppContext Removal — Phase B2 Validation

> **Owning task:** #1900 — Knowledge: Remove legacy AppContext fields and dual-paths (Phase B2)
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Is the B2 scope (from #1897 research) still accurate against current codebase? What risks exist, and can `knowledge_sources_refresh` migrate to `IngestCoordinator.refresh()` as specified?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (current) | Codebase | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` | Codebase | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` | Codebase | 1.0 |
| `serve/knowledge/src/owlbear_knowledge/refresh.py` | Codebase | 0.9 |
| `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` | Codebase | 0.9 |
| `.owlbear/research/mcp-knowledge-v2-migration.md` | Prior research | 0.9 |

## 3. Analysis

### 3.1 B1 Status (pre-requisite)

`_consolidation.py` is deleted. Consolidation methods were NOT migrated to `EnrichmentStore` — the feature was dropped rather than migrated. No consolidation tools remain in server. **B1 is satisfied (consolidation code removed); B2 can proceed.**

### 3.2 Validated B2 Scope — Pure Cleanup (Low Risk)

| Item | Current state | Migration action | Effort |
|------|---------------|------------------|--------|
| `search_knowledge` dual-path | `query_facade` primary, `query_service` fallback | Delete fallback branch + `_serialize_legacy_search_results()` | Low |
| `list_entities` | Deferred; uses old `graph_store.list_entities()` | Delete entirely | Trivial |
| `_legacy_graph_stats` / `_knowledge_stats_bridge` / `knowledge_stats_resource` | Use old `graph_store.get_counts()` | Delete — `knowledge_stats` tool already uses v2 | Trivial |
| `init_db()` wrapper | Calls `_schema_init_db(conn)` | Replace with `sqlite3.connect()` + explicit `ensure_tables()` calls (already present) | Low |
| AppContext dead fields | `structured_extractor`, `intra_doc_builder` | Remove fields + lifespan wiring | Trivial |
| `EnrichmentStore` wiring | `EnrichmentStore(db=conn, graph=gs)` (old GraphStore) | Change to `graph=graph_store_v2` — `SqliteGraphStore` implements protocol | Low |
| `IngestCoordinator` wiring | `IngestCoordinator(..., graph=gs)` (old GraphStore) | Change to `graph=graph_store_v2` — **also fixes latent bug** (see §3.4) | Low |
| Legacy imports | 10+ dead imports after above changes | Delete all | Trivial |

### 3.3 Blocked Item: `knowledge_sources_refresh`

| Aspect | Finding |
|--------|---------|
| Current impl | Creates `RefreshOrchestrator` per call with `select_content_fetcher(source.fetch_method)` |
| Target (per AC) | `ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))` |
| **Blocker** | `IngestCoordinator.refresh()` requires a `SourceFetcher` — **no implementation exists** |
| Protocol gap | `SourceFetcher` protocol defined in `protocols/fetcher.py` but zero concrete implementations |
| Old logic | `RefreshOrchestrator` has 3 source-type handlers (URL_LIST, FILE_GLOB, AUTHENTICATED_WEB) ~200 LOC |
| New requirement | Adapter ~100–150 LOC wrapping those fetch strategies into `SourceFetcher.fetch_source()` |

**Conclusion:** Migrating `knowledge_sources_refresh` is NOT a cleanup — it requires creating a new `SourceFetcher` adapter. This should be split into a separate task.

### 3.4 Latent Bug Found

`IngestCoordinator._process_document()` calls `self._graph.invalidate_evidence_by_chunks()` for REPLACED documents. Old `GraphStore` does NOT implement this method. The `AttributeError` is silently caught by a broad except clause, making re-ingest cascade silently incomplete. Switching to `graph_store_v2` fixes this.

### 3.5 Test Coverage

`knowledge_stats` tool already uses v2 APIs — tests pass. The `test_knowledge_tool_rename_1895.py` verifies tool registration and naming but not refresh internals. No direct test coverage for `_serialize_legacy_search_results()` or `list_entities` in the workspace test suite.

## 4. Recommendation (confidence: 0.85)

**Split B2 into two scoped tasks:**

| Sub-task | Scope | Risk | LOC delta |
|----------|-------|------|-----------|
| B2a — Pure cleanup | Remove dead fields, dual-paths, legacy stats/search fallback, list_entities, init_db, fix graph wiring | Low | −200, +10 |
| B2b — Refresh migration | Create `SourceFetcher` adapter, wire to `IngestCoordinator`, replace `knowledge_sources_refresh` | Medium | −80, +150 |

**Rationale:** B2a is safe, reversible, and achieves 80% of the cleanup value. B2b introduces new code and API surface — better isolated and tested separately.

Challenge: N/A — straightforward scope validation, no contested recommendation.

## 5. Follow-up Tasks

- **B2a (this task, revised scope):** Remove all legacy AppContext fields except `source_store` and `refresh_orchestrator`, remove dual-paths, fix graph wiring, delete dead imports and functions
- **B2b (new task):** Implement `SourceFetcher` adapter, pass to `IngestCoordinator`, replace `knowledge_sources_refresh` with v2 refresh path
