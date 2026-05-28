# Knowledge: Final Legacy File Sweep (Phase C) — Validation Pass

> **Owning task:** #1898 — Knowledge: Final legacy file sweep (Phase C)
> **Date:** 2026-05-28 **Status:** Complete (supersedes knowledge-phase-c-sweep.md)

## 1. Context and Question

Prior research (2026-05-27) identified #1898 as blocked on #1897 and #1900. Both are now archived/completed. This validation pass checks whether Phase C can proceed and revises the migration plan based on current codebase state.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/` file inventory | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (AppContext + lifespan) | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py` imports | Codebase | 0.9 |
| `serve/knowledge/src/owlbear_knowledge/protocols/` + `stores/` | Codebase | 0.9 |
| grep: all cross-references to legacy modules across workspace | Codebase | 1.0 |
| Test run: `test_mcp_knowledge_lifespan_1888.py` + `test_search_provenance.py` | Test output | 1.0 |

## 3. Analysis

### 3.1 Dependency Chain — RESOLVED

| Task | Status | Notes |
|------|--------|-------|
| #1897 (Phase B parent) | archived (completed) | — |
| #1900 (Phase B2a cleanup) | archived (completed) | — |
| #1898 (Phase C) | research | UNBLOCKED |

### 3.2 Legacy Files Present (13 total, all deletable)

12 listed + `extractor.py` (discovered dead):

| File | Status | Notes |
|------|--------|-------|
| source_store.py | Delete | Only consumer: `__init__.py` export + server TYPE_CHECKING |
| document_store.py | Delete | Only consumers are other legacy files |
| graph_store.py | Delete | Only consumers are other legacy files |
| graph_builder.py | Delete | Only consumers are other legacy files |
| status_store.py | Delete | One live import: `compute_content_hash` → migrate first |
| ingest.py | Delete | Only consumers are other legacy files |
| query_service.py | Delete | Only consumers are other legacy files |
| retrieval.py | Delete | Only consumers are other legacy files |
| refresh.py | Delete | Server TYPE_CHECKING only, field set to None |
| protocol.py | Delete | Two live imports → migrate first |
| models.py | Delete | Only non-legacy consumer was `extractor.py` (dead) |
| schema.py | Delete | Only consumer: `__init__.py` |
| **extractor.py** | Delete | Dead code — all 3 consumers are legacy files being deleted |

### 3.3 Non-Legacy Consumers Requiring Migration

Only **3 type migrations** needed (significantly simpler than prior research):

| Type | Current home | Target | Consumer(s) | LOC |
|------|------|------|------|------|
| `compute_content_hash` | `status_store.py` | `stores/content.py` (inline) | `stores/content.py` | ~8 |
| `HybridEmbedding` + `SparseVector` | `protocol.py` | `embeddings.py` | `qdrant.py` (runtime), `embeddings.py` (TYPE_CHECKING + lazy) | ~30 |
| `ContentFetcher` (Protocol) | `protocol.py` | `fetcher.py` | `_helpers.py` (TYPE_CHECKING) | ~5 |

### 3.4 EntityType/RelationType Conflict — RESOLVED

Prior research flagged this as a risk. It is no longer relevant:
- `extractor.py` was the only non-legacy consumer of old `EntityType`/`RelationType` from `models.py`
- `extractor.py` is dead code (zero non-legacy imports)
- Server already uses v2 enums from `protocols/common.py`
- No migration needed for these enums

### 3.5 AppContext Dead Fields

| Field | TYPE_CHECKING import | Lifespan value | Action |
|-------|-----|-----|------|
| `source_store: KnowledgeSourceStore \| None` | `from owlbear_knowledge.source_store` | `None` | Remove field + import |
| `refresh_orchestrator: RefreshOrchestrator \| None` | `from owlbear_knowledge.refresh` | `None` | Remove field + import |

### 3.6 Dead Test Files

| Test file | Failures | Reason |
|-----------|----------|--------|
| `test_mcp_knowledge_lifespan_1888.py` | 21 ERRORs (fixture setup) | References removed AppContext fields (`query_service`, `ingest_pipeline`) |
| `test_search_provenance.py` | 37 FAILED | Tests legacy `query_service` path that no longer exists |

### 3.7 Additional Deletions

| Item | Reason |
|------|--------|
| `__init__.py` | Rewrite — currently exports only from legacy modules |
| `serve/knowledge/README.md` | References legacy imports; needs rewrite |
| `tests/test_search_provenance.py` | Dead — tests removed legacy path |
| `tests/test_mcp_knowledge_lifespan_1888.py` | Dead — tests removed AppContext fields |

## 4. Recommendation (confidence: 0.90)

Execute as two sub-steps in a single task:

**C1 — Type migrations (~43 LOC moved, 3 files touched):**
1. Inline `compute_content_hash` into `stores/content.py`
2. Move `HybridEmbedding` + `SparseVector` into `embeddings.py`
3. Move `ContentFetcher` protocol into `fetcher.py`
4. Update imports in `qdrant.py`, `embeddings.py`, `_helpers.py`

**C2 — Deletion + rewrite:**
1. Remove `source_store` and `refresh_orchestrator` from AppContext; remove TYPE_CHECKING imports
2. Delete 13 files: 12 listed legacy + `extractor.py`
3. Delete 2 dead test files: `test_search_provenance.py`, `test_mcp_knowledge_lifespan_1888.py`
4. Rewrite `__init__.py` to export from `protocols/` and `stores/` only
5. Rewrite `serve/knowledge/README.md`

**Risk:** Low — all deletions are dead code or have type-migration coverage. Full test suite minus the 2 dead files should pass.

Challenge: SKIPPED — low-risk mechanical deletion after verified dead-code analysis. No contested recommendation.

## 5. Follow-up Tasks

No new tasks needed — scope is correctly defined in #1898 with minor additions (extractor.py deletion, 2 dead test files). Task body should be updated with revised plan.
