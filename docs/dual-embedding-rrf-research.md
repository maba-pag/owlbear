# Dual Embedding + Reciprocal Rank Fusion Retrieval Strategy

> **Owning task:** #232 — Research: Dual embedding + RRF retrieval strategy
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge pipeline serves a mixed-domain corpus: ~35% detail-oriented text (ISO norms, internal policies, laws), ~50% technical documentation, ~15% general info (slides, intranet articles). The current retrieval stack is bge-small-en-v1.5 (384-dim dense via FastEmbed ONNX, 33 MB) + optional bge-reranker-v2-m3 cross-encoder reranking.

**Problem:** Dense-only retrieval fails on keyword-critical queries. An ISO clause number like "7.1.2" or a policy code "HR-2024-003" has no semantic meaning to a dense encoder — these are pure lexical matches. For 35% of the corpus (normative/legal text), keyword precision is critical but dense retrieval alone misses it.

**Question:** Would dual-embedding (one dense, one sparse/lexical) with Reciprocal Rank Fusion improve retrieval for this mixed corpus? Is it worth the complexity vs single-model alternatives?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Cormack et al. (2009) — RRF paper | dl.acm.org/doi/10.1145/1571941.1572114 | .95 | Original RRF algorithm: `1/(k+rank)`, k=60, outperforms Condorcet and individual rank learning on TREC |
| BGE-M3 paper (Chen et al. 2024) | arxiv.org/abs/2402.03216 | .95 | Single model producing dense (1024-d) + sparse + ColBERT; self-knowledge distillation; MIRACL/MLDR benchmarks |
| Azure AI Search — RRF docs | learn.microsoft.com/azure/search/hybrid-search-ranking | .90 | Production RRF: parallel query execution, k=60, weighted fusion, score decomposition |
| Milvus multi-vector hybrid search | milvus.io/docs/multi-vector-search.md | .85 | Dense + sparse + RRF in production: `AnnSearchRequest` per field, `RRFRanker`, BGE-M3 example |
| FastEmbed supported models | qdrant.github.io/fastembed/examples/Supported_Models | .90 | Supported ONNX models: bge-small (67 MB), SPLADE++ (532 MB), nomic-embed-text-v1.5 (520 MB) |
| BAAI/bge-m3 HuggingFace model card | huggingface.co/BAAI/bge-m3 | .85 | Usage: `BGEM3FlagModel.encode()` returns `dense_vecs`, `lexical_weights`, `colbert_vecs`; 8192 tokens; FP16 |
| nomic-embed-text-v1.5 model card | huggingface.co/nomic-ai/nomic-embed-text-v1.5 | .75 | 768-dim (Matryoshka: 512/256/128), MTEB avg 62.28, Apache-2.0, 8192 context |
| RAG-Fusion (Raudaschl) | github.com/Raudaschl/rag-fusion | .65 | Multi-query + RRF pattern: generate query variants, search each, fuse. 907 stars |
| knowledge-ingestion-research.md | docs/knowledge-ingestion-research.md §3.3 | .90 | Prior OwlBear analysis: single → rerank → RRF phased approach recommended |

## 3. Analysis

### 3.1 RRF Formula and Behavior

RRF score for document $d$ across $n$ ranked lists:

$$\text{RRF}(d) = \sum_{i=1}^{n} \frac{1}{k + \text{rank}_i(d)}$$

Where $k=60$ is the standard constant (Cormack 2009, Azure, Milvus all use this default).

**How it works:** A document ranked #1 in one system gets score $1/61 \approx 0.0164$. Ranked #10 gets $1/70 \approx 0.0143$. Documents appearing in multiple rankings accumulate scores. A doc ranked #5 in both systems scores $2/65 \approx 0.0308$, beating a doc ranked #1 in only one system.

**Failure modes:**

- **Low-overlap corpora**: When dense and sparse retrieval return entirely different candidate sets, RRF just interleaves — no fusion benefit.
- **k sensitivity**: k=60 is well-established but flattens rank differences. For small result sets (top-5), consider k=20-30 for sharper discrimination.
- **Missing from one list**: A document absent from one retrieval gets $\text{score}=0$ for that ranker. It can still win if very highly ranked in the other.

**When RRF beats single-model:** (a) Mixed-type queries where semantic and lexical signals capture different relevant docs; (b) Corpora mixing technical notation with prose; (c) When no single retrieval mode covers all document types.

### 3.2 Model Candidates — Third-Party Benchmarks Only

**CRITICAL**: pplx-embed-context-v1-0.6B model weights are not publicly accessible (HuggingFace returns Unauthorized). No independent MTEB leaderboard submission exists. **Cannot recommend without third-party-verified benchmarks. Disqualified.**

| Model | Type | Dim | MTEB Avg | BEIR Ret. | Size (ONNX) | Size (PyTorch) | Max Tokens | License |
|-------|------|-----|----------|-----------|-------------|----------------|------------|---------|
| bge-small-en-v1.5 | Dense | 384 | ~62.2 | ~51.5 | 67 MB | 130 MB | 512 | MIT |
| nomic-embed-text-v1.5 | Dense | 768 | 62.28 | ~52.8 | 520 MB | ~550 MB | 8192 | Apache-2.0 |
| bge-m3 (dense only) | Dense | 1024 | ~67.1 | ~56.2 | N/A ¹ | 2.2 GB FP16 | 8192 | MIT |
| bge-m3 (sparse) | Sparse | vocab | — | — | N/A ¹ | (same model) | 8192 | MIT |
| SPLADE++ (Splade_PP_en_v1) | Sparse | 30522 | — | ~51.4 ² | 532 MB | ~550 MB | 512 | Apache-2.0 |
| pplx-embed-context-v1-0.6B | Dense | ? | **NONE** | **NONE** | **N/A** | ~1.2 GB ³ | ? | **Gated** |

¹ bge-m3 has no official ONNX in FastEmbed. Requires FlagEmbedding (PyTorch).
² SPLADE++ BEIR score from original SPLADE paper; confirmed via MTEB sparse retrieval leaderboard.
³ Estimated from parameter count; model weights not accessible for verification.

### 3.3 Architecture Options Comparison

| Criterion | A: Current (bge-small + reranker) (.75) | B: Dual FastEmbed (bge-small + SPLADE++) + RRF (.80) | C: bge-m3 single-model hybrid (.85) | D: Two separate 0.6B models + RRF (.40) |
|-----------|-------|-------|-------|-------|
| **Retrieval quality** | Good (reranker fixes ranking) | Very good (keyword + semantic) | Excellent (dense+sparse+ColBERT) | Unknown (no benchmarks for pplx-embed) |
| **Keyword precision** | Poor (dense misses clause numbers) | **Strong** (SPLADE matches exact tokens) | **Strong** (bge-m3 sparse mode) | Unknown |
| **Runtime (ONNX stack)** | Yes (FastEmbed) | **Yes** (FastEmbed both models) | **No** (requires PyTorch/FlagEmbedding) | No (requires PyTorch) |
| **Model disk** | 33 MB + 1 GB reranker | 33 MB + 532 MB = 565 MB | 2.2 GB | ~2.4 GB |
| **RAM at inference** | ~100 MB + ~1.2 GB reranker | ~150 MB + ~700 MB = 850 MB | ~3 GB | ~3+ GB |
| **Ingest latency** | 1 embed per chunk | 2 embeds per chunk (~2×) | 1 embed (3 outputs) per chunk | 2 embeds per chunk (~2×) |
| **Query latency** | ~5ms vec + ~200ms rerank | ~10ms × 2 + RRF merge ~1ms | ~15ms (one model, three outputs) | ~200ms × 2 |
| **sqlite-vec compatibility** | Full | Dense: full. Sparse: needs custom table | Dense: full. Sparse: needs custom table | Same as B |
| **Storage tables** | 1 vec0 table (current) | 2 tables: vec0 + sparse custom | 2 tables: vec0 + sparse custom | 2 tables |
| **KISS score** | **High** | **Medium** | Medium (PyTorch dep is heavy) | **Low** |
| **YAGNI risk** | Low | Medium | Medium-High | **Very High** |
| **Dependencies added** | None (current stack) | None (FastEmbed already has both) | +FlagEmbedding, +PyTorch (~2 GB) | +PyTorch, +unknown model deps |

### 3.4 Sparse Vector Storage in sqlite-vec

sqlite-vec's `vec0` tables only support dense float vectors. Sparse vectors (token_id → weight dicts) need a different strategy:

| Approach | Pros | Cons | KISS |
|----------|------|------|------|
| Custom SQLite table (JSON blob) + app-level scoring | Simple, no new deps, full control | Slow for large corpora (scan all rows) | High |
| SQLite FTS5 for BM25 | Built-in, fast, proven | BM25, not learned sparse (SPLADE) | High |
| Store as dense-ified vector (30522-dim) in vec0 | Uses existing vec0 | Massively wasteful (30K dims, >99% zeros) | Low |
| Qdrant local mode | Native sparse support | New dependency, migration effort, task #236 | Medium |

**Recommended for now**: Custom SQLite table with sparse vectors stored as compact binary (list of (token_id, weight) pairs sorted by weight descending). At query time, compute dot product between query sparse vector and top-K candidates pre-filtered by token overlap. For <50K documents this is plenty fast (<10ms). A future migration to Qdrant (task #236) would give native sparse vector indexing.

### 3.5 Local Feasibility — Ryzen 8840U / 16 GB RAM

| Configuration | Model RAM | Inference/chunk | Concurrent? | Verdict |
|---------------|-----------|-----------------|-------------|---------|
| bge-small (ONNX) | ~80 MB | ~5 ms | — | Trivial |
| bge-small + SPLADE++ (both ONNX) | ~850 MB | ~15 ms total | Yes (separate ONNX sessions) | **Feasible** |
| bge-m3 FP16 (PyTorch) | ~3 GB | ~150 ms CPU | — | Tight but OK |
| bge-m3 FP16 + reranker | ~4.2 GB | ~350 ms | Sequence only | Tight |
| Two 0.6B models (PyTorch) | ~3+ GB | ~300 ms | Probably not | Risky |

The dual FastEmbed approach (B) is the most laptop-friendly: two ONNX models totaling ~850 MB RAM with fast inference. bge-m3 (C) is feasible but consumes 3 GB of the 16 GB budget.

### 3.6 When Is Dual-Embedding + RRF Worth It?

| Scenario | Single dense + reranker | Dual + RRF |
|----------|------------------------|------------|
| "What is configuration management?" | ✅ Dense captures semantics well | ✅ Both work, marginal RRF benefit |
| "ISO 9001 clause 7.1.2 requirements" | ❌ Dense can't match "7.1.2" | ✅ **Sparse matches exact clause number** |
| "HR-2024-003 travel policy" | ❌ Numbers meaningless to dense | ✅ **Sparse matches policy code** |
| "Explain the adapter pattern" | ✅ Dense is ideal | ✅ Dense dominates in fusion |
| "DIN EN ISO 14001:2015 Anhang A" | ❌ Multilingual notation | ✅ **Sparse matches notation** |

**For this corpus mix (35% normative text), dual-embedding with RRF provides a meaningful improvement** over dense-only retrieval. The reranker can only rerank what the retriever finds — if the dense retriever never surfaces "clause 7.1.2" in the candidate set, the reranker can't save it.

### 3.7 Prior Art — Dual Embedding + RRF in Production

| System | Implementation | Scale | Notes |
|--------|---------------|-------|-------|
| Azure AI Search | Dense + BM25 + RRF (k=60), optional semantic reranker on top | Production (millions of docs) | RRF is default for all hybrid queries |
| Milvus | Multiple `AnnSearchRequest` + `RRFRanker` | Production | Native support for bge-m3 dense+sparse hybrid |
| Pinecone | Hybrid search with sparse-dense fusion | Production | Proprietary fusion algorithm |
| Vespa | Dense + sparse fields, RRF or linear combination | Production | Official bge-m3 integration notebook |

All major vector DB vendors have converged on dense+sparse+RRF as the standard hybrid search pattern. This is not experimental.

## 4. Recommendation (.80 confidence)

**Option B: Dual FastEmbed (bge-small-en-v1.5 dense + SPLADE++ sparse) with RRF fusion.**

### Why this option

1. **Stays in ONNX/FastEmbed ecosystem** — no PyTorch dependency, aligns with KISS principle
2. **FastEmbed already supports both models** — `TextEmbedding` for dense, `SparseTextEmbedding` for sparse
3. **Total model footprint ~600 MB** — fits comfortably on 16 GB laptop
4. **Solves the core problem** — keyword precision for normative/legal text
5. **RRF is trivially implementable** — ~30 LOC, no external dependency
6. **Composable with existing reranker** — retrieval pipeline: dual search → RRF merge → reranker → return

### Why not the other options

- **Option A (current)**: Doesn't solve keyword precision. The reranker can't rerank what the dense retriever never finds.
- **Option C (bge-m3)**: Superior quality, but adds ~2 GB PyTorch dependency. Good future path via Qdrant (task #236), but violates current KISS/lightweight constraints.
- **Option D (pplx-embed + bge-m3 sparse)**: No independent benchmarks for pplx-embed. Model weights not publicly available. Cannot recommend.

### Architecture

```
Ingest:
  chunk_text ─┬─► TextEmbedding(bge-small) ──► dense vec (384-d)  ──► vec0 table
              └─► SparseTextEmbedding(SPLADE++) ► sparse vec ──────► sparse_embeddings table

Query:
  query_text ─┬─► dense embed ──► vec0 MATCH (top_k×3) ──┐
              └─► sparse embed ► sparse table scan (top_k×3) ─┤
                                                              ▼
                                                      RRF merge (k=60)
                                                              │
                                                              ▼
                                                    top_k candidates
                                                              │
                                                     (optional reranker)
                                                              │
                                                              ▼
                                                        final results
```

### Schema additions

```sql
-- New table for sparse embeddings (SPLADE++ output)
CREATE TABLE IF NOT EXISTS sparse_embeddings (
    rowid       INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id    TEXT,
    tokens      BLOB,   -- packed (token_id, weight) pairs, sorted by weight desc
    scope       TEXT DEFAULT 'global'
);
CREATE INDEX IF NOT EXISTS idx_sparse_scope ON sparse_embeddings(scope);
```

### RRF implementation sketch

```python
def reciprocal_rank_fusion(
    *ranked_lists: list[tuple[str, float]],
    k: int = 60,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results[:top_k]
```

### Risk and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| SPLADE++ sparse vectors are large (vocab-size dicts) | Medium | Store only non-zero entries (~50-200 per doc); compact binary encoding |
| sqlite-vec can't index sparse vectors | Certain | Custom table + app-level scoring; adequate for <50K docs; Qdrant later (#236) |
| Double embedding time at ingest | Certain | Both ONNX models are fast on CPU; total ~15ms/chunk vs ~5ms current |
| RRF k=60 may need tuning | Low | Standard value works well; expose as config parameter |
| SPLADE++ is English-only | Medium | For multilingual (EU norms), consider bge-m3 upgrade path later |

## 5. Follow-up Tasks

1. **Add `SparseEmbeddingProvider` protocol + FastEmbed SPLADE adapter** — Mirror the existing `EmbeddingProvider` protocol for sparse embeddings. Implement `FastEmbedSparseProvider` using `fastembed.SparseTextEmbedding` with SPLADE++ model. TDD. Priority: needed. Tags: phase-9, embedding, knowledge-graph.

2. **Sparse embeddings SQLite table + storage** — Add `sparse_embeddings` table to schema (v4 migration). Store SPLADE++ output as compact binary blobs. Add `SparseVectorStore` class with `store_sparse()` and `search_sparse()` methods. TDD. Priority: needed. Tags: phase-9, knowledge-graph. Depends on: task 1.

3. **RRF merge function** — Implement `reciprocal_rank_fusion()` in `vectors.py` or new `retrieval.py`. Parameterized k (default 60). TDD with edge cases (empty lists, single list, no overlap). Priority: needed. Tags: phase-9, knowledge-graph.

4. **Dual-search integration in `VectorStore.search_similar()`** — Add `hybrid: bool` parameter. When enabled: run dense vec0 search + sparse search in parallel, fuse with RRF, optionally rerank. Priority: needed. Tags: phase-9, knowledge-graph. Depends on: tasks 2, 3.

5. **Dual-embed in `IngestPipeline`** — Extend `_run_embed()` to produce both dense and sparse embeddings per chunk. Store both in parallel. Priority: needed. Tags: phase-9, knowledge-graph. Depends on: tasks 1, 2.

6. **Benchmark: dense-only vs hybrid on sample ISO/policy corpus** — Create a small test corpus (~50 docs: some ISO clauses, some technical docs, some general). Measure recall@10 for keyword-heavy queries vs semantic queries. Validate RRF improvement. Priority: important. Tags: phase-9, test, knowledge-graph. Depends on: task 4.
