# Initial KB Data Load — Readiness Assessment

> **Owning task:** #178 — Execute initial KB data load and verify search quality
> **Date:** 2026-04-02 **Status:** Complete

## 1. Context and Question

Task #178 was blocked on #16 (mcp-knowledge server) and #160 (hybrid search). Both are now archived. This readiness assessment validates that the task can proceed, identifies AC gaps, and recommends AC refinements before implementation.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Task #16 (mcp-knowledge server) | kanban board (archived) | 1.0 — dependency resolved, 84 tests green |
| Task #160 (hybrid search upgrade) | kanban board (archived) | 1.0 — dependency resolved, 32 tests green |
| Task #176 (data loader script) | kanban board (archived) | 1.0 — loader.py built, 57 tests green |
| sources.yaml manifest | data/knowledge/general/sources.yaml | 1.0 — defines 3 glob sources |
| loader.py CLI | packages/knowledge/src/owlbear_knowledge/loader.py | 1.0 — verified CLI entry point |
| BgeM3EmbeddingProvider | packages/knowledge/src/owlbear_knowledge/embeddings.py | 1.0 — lazy model load, ~2.3 GB |
| QdrantVectorStore hybrid search | packages/knowledge/src/owlbear_knowledge/qdrant.py L188-221 | 1.0 — Prefetch+RRF+normalization |
| EntityExtractor (no-op path) | packages/knowledge/src/owlbear_knowledge/extractor.py L89-91 | 1.0 — returns empty without StructuredExtractor |
| Original research | docs/research/general-kb-initial-data-load.md | .95 — recommended ~80 docs (outdated count) |

## 3. Analysis

### 3.1 Dependency Status (All Clear)

| Upstream | Status | Evidence |
|----------|--------|----------|
| #16 mcp-knowledge server | Archived | 84 tests, .98 audit confidence |
| #160 hybrid search | Archived | 32 tests, .98 audit confidence |
| #176 data loader | Archived | 57 tests, loader.py functional |

### 3.2 Document Count Mismatch (Critical AC Gap)

| Glob | Original estimate | Actual count |
|------|------------------|--------------|
| docs/research/*.md | ~50 curated | **519** |
| skills/*/SKILL.md | ~25 | **23** |
| instructions/*.md | ~5 | **5** |
| **Total** | **~80** | **547** |

The AC says "~80 documents ingested." Reality: 547 files match the unfiltered globs. The original research recommended a "curated subset of ~50 high-signal research docs" but sources.yaml uses `docs/research/*.md` without curation. Options:

| Option | Pros | Cons | KISS? |
|--------|------|------|-------|
| A: Load all 547 | Simple, no curation effort | Longer ingestion (~5-20 min on CPU), more vector storage | **Yes** |
| B: Curate to ~80 | Matches original AC | Requires manual selection criteria, ongoing maintenance | No |

**Recommendation (.85):** Load all 547 (Option A). BgeM3 on CPU handles this volume, Qdrant in-memory is fast, delta detection prevents redundant re-ingestion on subsequent runs. Update AC to reflect ~550 documents.

### 3.3 Entity/Edge Counts Will Be Zero

Neither loader.py nor mcp-knowledge server inject a StructuredExtractor:
- loader.py L267: `extractor = EntityExtractor()` (no extractor= kwarg)
- server.py L85: `extractor = EntityExtractor(model)` (positional model, no extractor=)

Without an LLM-backed StructuredExtractor, EntityExtractor returns empty ExtractionResult. The AC says "get_stats shows expected document/entity/edge counts" but entity_count and edge_count will be 0. This is acceptable — hybrid search operates on document chunk embeddings, not graph entities. Graph expansion provides no value until entities are populated.

### 3.4 Hybrid Search Comparison Methodology

AC: "Hybrid search returns better results than dense-only for at least 3/5 queries." The comparison requires calling QdrantVectorStore.search_similar twice per query:
1. With HybridEmbedding(dense, sparse) — hybrid path (Prefetch+RRF)
2. With plain dense vector (list[float]) — dense-only path

BgeM3EmbeddingProvider.embed_hybrid() returns both dense and sparse vectors; BgeM3EmbeddingProvider.embed() returns dense-only. Builder can test both paths.

### 3.5 Runtime Requirements

| Requirement | Detail |
|-------------|--------|
| BgeM3 model | ~2.3 GB download on first run (cached in ~/.cache/huggingface/) |
| Qdrant | In-memory default (no external service needed) |
| SQLite | data/knowledge/knowledge.db (created by loader) |
| CPU time | ~5-20 min for 547 docs on laptop CPU (BgeM3 is compute-heavy) |

## 4. Recommendation (.90 confidence)

Task is ready to proceed. Refine AC to match reality before moving to backlog:
1. Update document count: "~80" to "~550" (or "all files matching sources.yaml globs")
2. Clarify entity/edge counts: "entities: 0, edges: 0 (no LLM extractor wired — expected)"
3. Add agent definitions and decision records as optional wave 2 sources
4. Note BgeM3 first-run model download requirement

Challenge: SKIP — info-only readiness assessment, no recommendation requiring challenge.

## 5. Follow-up Tasks

AC refinements applied directly to #178 task body (Channel B). No new tasks needed — all infrastructure exists. The task transitions to backlog for architect review of the refined AC.
