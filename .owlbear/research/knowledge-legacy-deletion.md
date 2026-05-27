# Knowledge: Legacy Code Deletion — Feasibility & Sequencing

> **Owning task:** #1883 — Knowledge: Legacy code deletion
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Can all 14 listed legacy files be deleted in a single pass? What's the blast radius and sequencing?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/` directory listing | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` imports + AppContext | Codebase | 1.0 |
| grep across 30+ files for legacy module imports | Codebase | 1.0 |
| `protocols/__init__.py` and `stores/__init__.py` — replacement surface | Codebase | 0.9 |

## 3. Analysis

### 3.1 File-by-file deletion readiness

| Legacy file | Imported by non-legacy code? | Blocking factor |
|-------------|------------------------------|-----------------|
| `_enrichment.py` (mcp) | **No** — dead code | None. Delete immediately. |
| `_consolidation.py` (mcp) | **Yes** — server.py active tools | Consolidation not in EnrichmentStore yet |
| `source_store.py` | server.py, loader.py | Server still builds `KnowledgeSourceStore` |
| `document_store.py` | server.py, loader.py | Server still builds `DocumentStore` |
| `graph_store.py` | server.py, loader.py | Server still builds old `GraphStore` (differs from `SqliteGraphStore`) |
| `graph_builder.py` | server.py | Server still creates `IntraDocGraphBuilder` |
| `status_store.py` | stores/content.py imports `compute_content_hash` | 1 internal dependency |
| `ingest.py` | server.py | Server still builds `IngestPipeline` |
| `query_service.py` | server.py (fallback path) | Used when `query_facade` is None |
| `retrieval.py` | server.py | Server still creates `GraphAugmentedRetriever` |
| `refresh.py` | server.py | `RefreshOrchestrator` still in AppContext |
| `protocol.py` | _helpers.py (TYPE_CHECKING) | Trivial removal |
| `models.py` | 20+ files (tests, server, stores) | Most used; types differ from `protocols/common.py` |
| `schema.py` | server.py `init_db()`, 6 tests | Old DDL still runs before `ensure_tables()` |

### 3.2 `models.py` vs `protocols/common.py` incompatibility

Old `models.py` has 30+ EntityType/RelationType values. New `protocols/common.py` has a lean 12+13 set (D10 design). These are NOT drop-in replacements — callers using old enum values will break.

### 3.3 MCP server dual-path architecture

The `AppContext` carries **both** legacy and new fields. The `search_knowledge` tool tries `query_facade` first, falls back to `query_service`. The `store_enrichment` tool uses `EnrichmentStore` for phase-1 but `_consolidation.py` for phase-2.

### 3.4 Test files — pure legacy (safe to delete)

9 test files test **only** legacy code: `test_manifest_loader_1578.py`, `test_ingest_1656.py`, `test_query_service.py`, `test_browser_fetcher_wiring.py`, `test_qdrant_source_identity.py`, `test_enrichment_schema.py`, `test_schema_bookmark_drop_1583.py`, `test_schema_constraint_enforcement_1586.py`, `test_enrichment_persistence_1557.py`.

### 3.5 `loader.py` — unlisted legacy

`loader.py` is 100% wired to legacy modules (imports `DocumentStore`, `GraphStore`, `IngestPipeline`, `schema.init_db`, `KnowledgeSourceStore`). Not in deletion list but has no non-legacy consumers. Only used via `python -m owlbear_knowledge.loader`.

## 4. Recommendation (confidence: 0.85)

**Three-phase deletion** is required; single-pass deletion will break the running MCP server.

| Phase | Scope | Complexity |
|-------|-------|------------|
| A — Dead code | Delete `_enrichment.py`, 9 test files, `loader.py`. No functional impact. | Low |
| B — Server migration | Remove legacy AppContext fields, dual-path logic; wire all tools exclusively to new stores. Move `_consolidation.py` logic into `EnrichmentStore`. Remove `query_service` fallback. | Medium-High |
| C — Final sweep | Delete remaining 12 legacy files. Rewrite `__init__.py`. Remove `schema.py` (stores own their DDL). Fix `stores/content.py` import of `compute_content_hash`. | Medium |

Challenge: N/A — straightforward sequencing analysis, no contested recommendation.

## 5. Follow-up Tasks

- Phase A: dead-code deletion (immediate, no risk)
- Phase B: MCP server v2-only migration (medium effort, prerequisite for Phase C)
- Phase C: final legacy file sweep (blocked on B)
