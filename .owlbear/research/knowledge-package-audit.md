# Knowledge Package Architectural Audit

**Date:** 2026-05-25 (updated)  
**Scope:** `serve/knowledge/` (owlbear_knowledge) + `serve/mcp-knowledge/` (owlbear_mcp_knowledge)

## Context

The knowledge subsystem has undergone multiple architectural pivots. Dead-code modules from earlier pivots (`evaluator.py`, `benchmark.py`, `llm_extractor.py`, `inter_doc_graph_builder.py`) have been removed. This audit reflects the current state.

---

## Pass 1 — Structural: Import Graph + Public API

### owlbear_knowledge (25 modules, ~5 500 LOC)

| Module | Lines | Internal Imports | Public API |
|--------|-------|-----------------|-----------|
| `__init__.py` | — | cancellation, document_store, graph_store, ingest, intake, models, query_service, refresh, retrieval, schema, source_store, status_store | 21 re-exported names |
| `_paths.py` | ~20 | — | `sandbox_path` |
| `_ssrf.py` | ~30 | — | `SSRFProtectionError`, `check_url_allowed` |
| `cancellation.py` | ~40 | — | `CancelSignal` (Protocol), `LinkedCancelSignal` |
| `chunker.py` | ~200 | — | `Chunk`, `TextChunker` |
| `content_safety.py` | ~50 | — | `should_wrap`, `wrap_untrusted_content` |
| `document_store.py` | ~450 | status_store | `DocumentStore` |
| `embeddings.py` | ~130 | protocol (TYPE_CHECKING) | `EmbeddingProvider` (Protocol), `BgeM3EmbeddingProvider` |
| `extractor.py` | ~60 | models | `ExtractionResult`, `EntityExtractor`, `EXTRACTION_PROMPT` |
| `fetcher.py` | ~15 | _ssrf | `HttpxContentFetcher` |
| `graph_builder.py` | ~150 | models, protocol | `GraphBuildResult`, `IntraDocGraphBuilder`, `GRAPH_BUILDER_PROMPT` |
| `graph_store.py` | ~650 | models | `GraphStore` |
| `ingest.py` | ~550 | content_safety, _paths, models | `IngestResult`, `IngestPipeline` |
| `intake.py` | ~80 | _paths, fetcher | `IntakeResult`, `read_file`, `read_url`, `read_text` |
| `integrity.py` | ~130 | — | `audit_integrity` |
| `loader.py` | ~400 | intake, _paths, models, source_store | `ManifestEntry`, `LoadSummary`, `load_manifest` |
| `models.py` | ~170 | — | `EntityType`, `RelationType`, `SourceType`, `KnowledgeSource`, `Entity`, `Edge`, `PageStatus`, `SourcePage`, `Document` |
| `protocol.py` | ~100 | — | `SparseVector`, `HybridEmbedding`, `Embedding`, `VectorStoreProtocol`, `StructuredExtractor`, `ContentFetcher` |
| `qdrant.py` | ~400 | protocol | `QdrantVectorStore`, `COLLECTION_NAME`, `DENSE_DIM` |
| `query_service.py` | ~250 | (TYPE_CHECKING: embeddings, graph_store, retrieval, source_store, protocol) | `KnowledgeQueryError`, `StructuredSearchResult`, `KnowledgeQueryService` |
| `refresh.py` | ~500 | _paths, intake, models, ingest, source_store | `RefreshResult`, `RefreshOrchestrator` |
| `retrieval.py` | ~200 | protocol, models | `RetrievalResult`, `GraphAugmentedRetriever` |
| `schema.py` | ~500 | integrity | `init_db`, `audit_integrity` (re-export) |
| `source_store.py` | ~250 | models | `KnowledgeSourceStore` |
| `status_store.py` | ~130 | — | `DocumentStatus`, `compute_content_hash`, `StatusStore` |

**Import edge summary:**
- 0 circular dependencies ✓
- Hub nodes: `models` (8 incoming), `protocol` (4 incoming), `_paths` (3 incoming)
- Import direction: strictly top-down

### owlbear_mcp_knowledge (7 modules, ~2 200 LOC)

| Module | Lines | Internal Imports | Cross-Package | Public API |
|--------|-------|-----------------|---------------|-----------|
| `server.py` | ~1100 | _consolidation, _enrichment, _helpers, _types | 15+ owlbear_knowledge imports | 15 MCP tool functions |
| `_enrichment.py` | ~400 | _helpers, _types | models.EntityType | (private) |
| `_consolidation.py` | ~300 | _helpers, _types | — (via _helpers) | (private) |
| `_helpers.py` | ~250 | _types | fetcher, models, protocol | (private, 17+ functions) |
| `_types.py` | ~100 | — | — | TypedDicts + constants |
| `__init__.py` | — | — | — | (empty) |
| `__main__.py` | — | server | — | entry point |

---

## Pass 2 — Architectural Assessment

### Layer Map

| Layer | Modules | Responsibility |
|-------|---------|---------------|
| L0 – Domain | models, protocol, cancellation | Data classes, protocols, enums |
| L1 – I/O | _paths, _ssrf, fetcher, chunker, embeddings, content_safety | Sandboxed access, HTTP, text ops |
| L2 – Storage | schema, integrity, status_store, source_store, document_store, graph_store, qdrant | SQLite + Qdrant persistence |
| L3 – Processing | extractor, graph_builder | Entity extraction, graph construction |
| L4 – Orchestration | intake, ingest, refresh, loader | Pipelines and lifecycle |
| L5 – Query | retrieval, query_service | Hybrid search + structured results |
| L6 – MCP | server, _enrichment, _consolidation, _helpers, _types | Tool exposure + enrichment logic |

**Import direction:** Strictly top-down ✅. No circular deps.

### Smell Catalogue

| # | Sev | Issue | Module(s) | Root Cause |
|---|-----|-------|-----------|-----------|
| 1 | 🔴 | **God module** — 1100+ lines, 15 tools, DI, lifespan, direct SQL | `server.py` | Accretion; no extraction discipline |
| 2 | 🔴 | **Mixed ownership** — writes chunks AND delegates to graph_store for entities; dual embedding API (new vs. legacy path) | `document_store.py` | Feature accretion; unclear boundary |
| 3 | 🟠 | **Orchestrates 6+ concerns** — chunking, extraction, safety, persistence, source creation, delta detection | `ingest.py` | Pipeline grew without decomposition |
| 4 | 🟠 | **4 handler types in one class** — url_list, file_glob, authenticated_web, inline, each ~100 LOC | `refresh.py` | Strategy pattern missing |
| 5 | 🟠 | **Schema + parsing + orchestration + source CRUD** all mixed | `loader.py` | No parser/processor split |
| 6 | 🟠 | **Deeply nested validation** — 4+ chained validators, hard to follow | `_enrichment.py` | Incremental validation patches |
| 7 | 🟡 | **Catch-all helpers** — 20+ unrelated functions (normalization, extraction, serialization, validation) | `_helpers.py` | No submodule discipline |
| 8 | 🟡 | **Hybrid search + RRF ranking** — 80+ lines of Qdrant-specific ranking embedded in store | `qdrant.py` | Search strategy not extracted |
| 9 | 🟡 | **DRY violation** — URL-extraction-from-config duplicated across 3 modules | ingest, refresh, source_store | No shared utility |
| 10 | 🟡 | **Direct SQL in MCP tools** — complex CTEs for enrichment claiming, no repository abstraction | `server.py` | Shortcut during enrichment build |
| 11 | 🔵 | `_canonicalize()` utility in models.py | `models.py` | Minor; should be text utility |
| 12 | 🔵 | Dead code: `ContentInjectionGuard` patch target | `server.py` | Abandoned guard feature |

### Boundary Violations

| From | To | Issue |
|------|----|----|
| `document_store` | `graph_store` | Persistence facade calls into data-access for entity/edge writes — who owns? |
| `server.py` | raw SQL | MCP tool functions run complex CTEs; bypasses any repository layer |
| `ingest.py` | `source_store` | Orchestration layer creates/resolves sources directly |

### What's Clean

- Zero circular imports (TYPE_CHECKING used correctly)
- Protocol-based DI throughout (VectorStoreProtocol, StructuredExtractor, ContentFetcher)
- Schema migrations (v1→v15) with idempotent `init_db()`
- Immutable Pydantic models (all frozen=True)
- `graph_store.py` — focused, clean CRUD
- Foundation layer (models, protocol, cancellation, integrity) — all single-responsibility
- MCP-knowledge depends only downward — adapter pattern respected

---

## Recommendations (Priority Order)

### Tier 1 — Critical (blocks maintainability)

1. **Split `server.py`** into tool modules + init/lifespan module (~5 files)
2. **Clarify document_store vs. graph_store ownership** — DocumentStore should own chunks only; IngestPipeline calls graph_store directly for entities
3. **Remove dual embedding API** — audit tests, kill legacy `store_embeddings` codepath

### Tier 2 — Major (reduces testability)

4. **Decompose IngestPipeline** into orchestrator + phases (or delegate batch ops to DocumentStore)
5. **Extract refresh handlers** into strategy classes (URLListHandler, FileGlobHandler, AuthenticatedWebHandler)
6. **Split loader.py** — ManifestParser (schema + parsing) vs. ManifestProcessor (orchestration)
7. **Create repository layer** for enrichment queue + consolidation candidates (remove raw SQL from tools)

### Tier 3 — Moderate (improves clarity)

8. Split `_helpers.py` into focused modules (_normalization, _serialization, _validation)
9. Extract hybrid search strategy from qdrant.py
10. Centralize URL-from-config extraction
11. Move `_canonicalize()` out of models.py

### Tier 4 — Minor (polish)

12. Remove dead `ContentInjectionGuard` patch target
13. Replace magic constants (batch threshold = 80)
14. Clarify AppContext wiring (structured_extractor lifecycle)
