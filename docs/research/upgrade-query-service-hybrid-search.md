# Upgrade query_service.py — Hybrid Search Gap Analysis

> **Owning task:** #160 — Upgrade query_service.py with retriever delegation and hybrid search
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #160 (split from #34) calls for three upgrades: (a) `query_for_context()` text formatting, (b) retriever delegation via `_search_chunks()`, (c) Qdrant hybrid search with prefetch+RRF. Dependency #159 is archived (work delivered under #205). **Key question:** What remains to implement vs what already exists in v2?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| v2 query_service.py (local) | `packages/knowledge/src/owlbear_knowledge/query_service.py` | 1.0 | Current 167 LOC — has `query_for_context`, `query`, retriever param |
| v2 retrieval.py (local) | `packages/knowledge/src/owlbear_knowledge/retrieval.py` | 1.0 | Standalone `query_for_context()` + `GraphAugmentedRetriever` (248 LOC) |
| v2 qdrant.py (local) | `packages/knowledge/src/owlbear_knowledge/qdrant.py` | 1.0 | Dense-only `search_similar()`, sparse config in collection, 196 LOC |
| v1 query_service.py (local) | `v1/src/owlbear/memory/knowledge/query_service.py` | 1.0 | Full pipeline: `_search_chunks()` delegation, `_format_docs()`, expansion |
| v1 qdrant.py (local) | `v1/src/owlbear/memory/knowledge/qdrant.py` | 1.0 | `_hybrid_search()` with prefetch + ColBERT rescore, `_dense_search()` |
| v1 benchmark search.py (local) | `v1/tests/benchmarks/search.py` | .95 | `_hybrid_rrf_search()` uses `FusionQuery(Fusion.RRF)` — cleanest pattern |
| Qdrant hybrid queries docs | qdrant.tech/documentation/concepts/hybrid-queries/ | .90 | Prefetch + Fusion.RRF server-side ranking pattern |
| dual-embedding-rrf.md (internal) | `docs/research/dual-embedding-rrf.md` | .90 | RRF formula, model selection, architecture decision |
| knowledge-package-integration.md (internal) | `docs/research/knowledge-package-integration-hybrid-search.md` | .95 | Parent research — decomposed #34 into #159/#160 |
| qdrant-client v1.9+ API (local verification) | Installed package | .95 | Verified `Fusion.RRF`, `FusionQuery`, `Prefetch` available |

## 3. Analysis

### 3.1 AC Gap Assessment

| AC Item | v2 Status | Gap | Action |
|---------|-----------|-----|--------|
| `query_for_context(prompt, max_tokens, top_k)` → formatted text or None | **Done** — exists in both `query_service.py` and `retrieval.py` | None | Verify tests pass |
| `KnowledgeQueryService` accepts retriever, delegates `_search_chunks()` | **Partial** — constructor accepts retriever; `query_for_context()` delegates; `query()` ignores retriever | `query()` still does direct search when retriever is set | Add `_search_chunks()` method |
| `QdrantVectorStore` hybrid search via prefetch+RRF | **Not done** — `search_similar()` extracts dense only from `HybridEmbedding` | Full hybrid path missing | Add `_hybrid_search()` + `_dense_search()` |
| Hybrid returns results from both indexes | **Not done** | Blocked by above | Same implementation |
| Fallback to dense-only when no sparse | **Not done** | Need conditional prefetch | Sparse-absent guard in `_hybrid_search()` |
| Unit tests for delegation + direct paths | **Partial** — tests exist for `query_for_context` in retrieval.py | Missing: hybrid Qdrant tests, delegation in `query()` | New test class |

### 3.2 Qdrant Hybrid Search — Implementation Pattern

The v1 benchmark provides the cleanest pattern (confirmed working locally):

```python
# Server-side RRF: prefetch sparse+dense, fuse with Fusion.RRF
result = client.query_points(
    collection_name=collection,
    prefetch=[
        Prefetch(query=SparseVector(...), using="sparse", limit=top_k * 10),
        Prefetch(query=dense_vec, using="dense", limit=top_k * 10),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    limit=top_k,
    with_payload=True,
)
```

**vs v1 approach (ColBERT rescore):** v1 uses ColBERT as final rescore step but falls back to dense-only when ColBERT is absent — losing sparse benefit. The RRF-only pattern is simpler (KISS) and preserves both dense+sparse signals without requiring a third vector type.

**Fallback strategy:** When `HybridEmbedding.sparse is None`, skip the sparse prefetch. The prefetch list then contains only dense, and `Fusion.RRF` with a single list is equivalent to dense-only search. Alternatively, fall back to `_dense_search()` directly for clarity.

### 3.3 `_search_chunks()` Delegation Pattern

v1 `KnowledgeQueryService._search_chunks()` (the actual pattern to port):

```
if self._retriever is not None:
    result = retriever.retrieve(prompt, top_k, scopes)
    return result.chunks, result.expansion_text
else:
    embedding = self._embed(prompt)
    results = vector_store.search_similar(embedding, top_k, ...)
    return results, ""
```

**v2 gap:** `query()` (async, returns `StructuredSearchResult` list) bypasses retriever entirely. Both `query()` and `query_for_context()` should go through `_search_chunks()`.

### 3.4 Scope and Complexity

| Change | File | LOC (estimate) | Complexity |
|--------|------|----------------|------------|
| Add `_hybrid_search()` and `_dense_search()` | qdrant.py | +40 | Low — port from v1 benchmark pattern |
| Update `search_similar()` dispatch | qdrant.py | ~5 (modify existing) | Trivial |
| Add `_search_chunks()` delegation | query_service.py | +20 | Low — port from v1 |
| Refactor `query()` to use `_search_chunks()` | query_service.py | ~15 (modify existing) | Low |
| New tests for hybrid Qdrant search | tests/ | +60 | Medium — need sparse+dense fixtures |
| New tests for delegation paths in query_service | tests/ | +40 | Low |
| **Total** | | **~180 LOC** | **Low-Medium** |

## 4. Recommendation (.90 confidence)

**Proceed with implementation as-is.** The AC is well-scoped and actionable. The main work is the Qdrant hybrid search (~40 LOC) plus wiring `_search_chunks()` delegation (~20 LOC). Patterns are proven in v1 and validated locally.

**Key implementation decisions (already settled):**
- Use `FusionQuery(Fusion.RRF)` for server-side RRF (not app-level) — KISS, fewer LOC
- Prefetch multiplier: 10x (proven in v1)
- Skip ColBERT rescore (deferred, current AC explicitly excludes it)
- Fallback: `_hybrid_search()` with sparse-absent guard → dense-only prefetch

**Risks (low):**
- `qdrant-client >= 1.9.0` is already specified and installed — API verified
- Sparse vectors stored via `store_embedding()` already work — only search path is missing
- No dependency on #33 (ingest pipeline) — hybrid search works with manually stored embeddings

**AC refinement suggestion:** Mark AC items 1 and 3-5 as the core deliverables. AC item 2 (`_search_chunks()`) should clarify that both `query()` and `query_for_context()` use it.

## 5. Follow-up Tasks

No new tasks needed — #160 itself is the implementation task. AC is valid and ready for architect gate.
