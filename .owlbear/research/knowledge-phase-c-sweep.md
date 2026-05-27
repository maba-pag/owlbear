# Knowledge: Final Legacy File Sweep (Phase C) — Readiness Assessment

> **Owning task:** #1898 — Knowledge: Final legacy file sweep (Phase C)
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Can Phase C (delete 12 legacy files, rewrite `__init__.py`) proceed? What's the actual dependency state and what additional work does deletion require?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/` directory + imports | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` imports | Codebase | 1.0 |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py` imports | Codebase | 1.0 |
| `.owlbear/research/knowledge-legacy-deletion.md` (parent research) | Prior research | 0.9 |
| `.owlbear/research/consolidation-migration-conflict.md` | Prior research | 0.8 |
| Task #1899 (Phase B1) and #1900 (Phase B2) status | Kanban | 1.0 |

## 3. Analysis

### 3.1 Dependency Chain Is Broken

| Task | Status | Actual state |
|------|--------|------|
| #1897 (Phase B parent) | archived (decomposed) | dep_status "ok" — misleading |
| #1899 (Phase B1 consolidation) | research, **blocked** | T3 decision pending |
| #1900 (Phase B2 server cleanup) | research, dep-blocked on #1899 | Cannot start |
| #1898 (Phase C) | research, dep on #1897 | dep_status "ok" but B is NOT done |

**Conclusion:** #1898 must depend on #1900, not #1897. Phase C cannot execute until the MCP server is fully v2-only (Phase B2 removes all legacy AppContext fields).

### 3.2 Non-Legacy Consumers of To-Delete Modules

After Phase B removes server.py and legacy-only imports, these **non-legacy** files still import from deletion targets:

| Consumer | Imports from | Type |
|----------|------|------|
| `stores/content.py` (v2) | `status_store.compute_content_hash` | Runtime |
| `embeddings.py` | `protocol.HybridEmbedding`, `protocol.SparseVector` | Runtime |
| `qdrant.py` | `protocol.HybridEmbedding` | Runtime |
| `extractor.py` | `models.Entity`, `models.Edge`, `protocol.StructuredExtractor` | Runtime |
| `_helpers.py` (mcp) | `models.Edge`, `models.EntityType`, `models.RelationType` | Runtime |

These files are NOT legacy — they're still used by v2 stores and the MCP server. Deleting `protocol.py` and `models.py` without migration will break them.

### 3.3 Migration Plan for Non-Deletable Types

| Type | Current home | Proposed new home | Rationale |
|------|------|------|------|
| `compute_content_hash` | `status_store.py` | `stores/content.py` (inline) | Only consumer; ~8 LOC |
| `HybridEmbedding` + `SparseVector` | `protocol.py` | `embeddings.py` | Co-located with EmbeddingProvider |
| `StructuredExtractor` | `protocol.py` | `extractor.py` | Only consumer |
| `VectorStoreProtocol` | `protocol.py` | Delete (only legacy consumers) | — |
| `ContentFetcher` | `protocol.py` | Delete (v2 has `SourceFetcher` in protocols/) | — |
| `Entity`, `Edge` (Pydantic) | `models.py` | `extractor.py` (private) | Only used for extraction output shape |
| `EntityType`, `RelationType` (old) | `models.py` | **Problem — see §3.4** | — |
| `KnowledgeSource`, `SourceType` | `models.py` | Delete (only legacy consumers after Phase B) | — |
| `PageStatus`, `SourcePage`, `Document` | `models.py` | Delete (only legacy/__init__.py) | — |

### 3.4 EntityType/RelationType Conflict in `_helpers.py`

`_helpers.py` imports old `EntityType` and `RelationType` enums (30+ values each) at RUNTIME. The v2 `protocols/common.py` has leaner sets (12+13 values). After Phase B, `_helpers.py` must switch to v2 enums — but this changes behavior if it references values absent from v2.

**Resolution:** Phase B2 (#1900) should handle this migration as part of "wire all MCP tools to v2 APIs". If it doesn't, Phase C must.

### 3.5 Additional Deletions (Beyond Task Scope)

| File | Reason |
|------|--------|
| `test_search_provenance.py` | Tests legacy `query_service` path; dead after Phase B |
| `serve/knowledge/README.md` | References legacy imports; needs rewrite |
| `loader.py` | 100% legacy-wired (already identified in parent research) |

### 3.6 Trade-off: Single-pass vs Sub-phased Phase C

| Approach | Risk | Effort | Confidence |
|----------|------|--------|-----------|
| **Single pass** (delete all + migrate types in one commit) | Medium — many moving parts | Medium (~150 LOC changes) | 0.75 |
| **Sub-phased** (C1: migrate types, C2: delete files) | Low — each step is independently testable | Low per step | 0.85 |

## 4. Recommendation (confidence: 0.85)

1. **Fix dependency:** Add #1900 as dependency on #1898 (replaces #1897 which is a decomposed shell).
2. **Block task** until Phase B (#1899 decision + #1900 implementation) completes.
3. **When unblocked**, execute as two sub-steps:
   - C1: Migrate `compute_content_hash`, `HybridEmbedding`/`SparseVector`, `StructuredExtractor`, `Entity`/`Edge` to their surviving consumers.
   - C2: Delete 12 legacy files + `loader.py` + `test_search_provenance.py`, rewrite `__init__.py` and README.

Challenge: SKIPPED — task is blocked; recommendation is sequencing analysis, not a contested choice.

## 5. Follow-up Tasks

- Fix dependency chain (#1898 → #1900) — immediate action
- No new tasks created — Phase C scope is already correctly defined, just needs prerequisite completion
