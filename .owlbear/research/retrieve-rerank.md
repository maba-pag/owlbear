# Retrieve-and-Rerank Strategy Research

> **Owning task:** #233 — Research: Retrieve-and-rerank strategy (pplx-embed + bge-reranker)
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge subsystem stores a mixed-domain corpus (~35% regulatory/ISO norms, ~50% technical docs, ~15% general info). The current retrieval pipeline uses:

- **Embedding**: `BAAI/bge-small-en-v1.5` (33M params, 384d, 512 tokens) via FastEmbed ONNX
- **Reranker**: `BAAI/bge-reranker-v2-m3` (568M params) via FlagEmbedding `FlagReranker`
- **Vector store**: sqlite-vec with `search_similar()` → optional two-stage reranking

**Question**: Can we improve retrieval quality by upgrading the embedding model (possibly to pplx-embed-context-v1-0.6B) and/or the reranker, while staying within local resource constraints (Ryzen 8840U, 16GB RAM)?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| BAAI/bge-large-en-v1.5 (HF) | <https://huggingface.co/BAAI/bge-large-en-v1.5> | .90 | MTEB scores, model specs, ONNX availability |
| BAAI/bge-m3 (HF) | <https://huggingface.co/BAAI/bge-m3> | .85 | Multi-functionality (dense+sparse+colbert), 8192 tokens |
| nomic-embed-text-v1.5 (HF) | <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5> | .90 | Matryoshka dimensions, 8192 tokens, MTEB scores |
| jina-embeddings-v3 (HF) | <https://huggingface.co/jinaai/jina-embeddings-v3> | .70 | 572M params, CC-BY-NC-4.0 (non-commercial) |
| pplx-embed-context-v1-0.6B (HF) | <https://huggingface.co/pplx/pplx-embed-context-v1-0.6B> | .95 | **Returned HTTP 401 Unauthorized — gated/private** |
| BAAI/bge-reranker-v2-m3 (HF) | <https://huggingface.co/BAAI/bge-reranker-v2-m3> | .90 | Reranker specs, BEIR eval, usage with FlagReranker |
| cross-encoder/ms-marco-MiniLM-L-12-v2 (HF) | <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2> | .75 | 33M param lightweight reranker, MS Marco benchmarks |
| jina-reranker-v2-base-multilingual (HF) | <https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual> | .80 | 278M params, BEIR/MIRACL eval, CC-BY-NC-4.0 |
| FastEmbed supported models | <https://qdrant.github.io/fastembed/examples/Supported_Models/> | .95 | ONNX model list, TextCrossEncoder models |
| SBERT Retrieve & Re-Rank guide | <https://www.sbert.net/examples/applications/retrieve_rerank/> | .85 | Canonical architecture description, bi-encoder + cross-encoder |
| Wang et al. 2024 "Best Practices in RAG" | <https://arxiv.org/abs/2407.01219> | .80 | RAG pipeline analysis: retrieval + reranking strategy |
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | .85 | Multi-functionality embedding, sparse+dense hybrid |

## 3. Analysis

### 3.1 pplx-embed-context-v1-0.6B — Availability Verdict

**Result: NOT VIABLE.**

- HuggingFace page (`pplx/pplx-embed-context-v1-0.6B`) returns **HTTP 401 Unauthorized** — weights are gated or proprietary
- No independent MTEB submission found on the MTEB leaderboard
- No ONNX export available, no FastEmbed support
- The "5-10x improvement" marketing claims cannot be verified against any third-party benchmark
- **Recommendation**: Drop pplx-embed from consideration entirely

### 3.2 Embedding Model Comparison (MTEB third-party benchmarks)

| Model | Params | Dim | Max Tokens | MTEB Avg | Retrieval Avg | ONNX Size | FastEmbed | License |
|-------|--------|-----|------------|----------|---------------|-----------|-----------|---------|
| bge-small-en-v1.5 **(current)** | 33M | 384 | 512 | 62.17 | 51.68 | 0.07 GB | Yes | MIT |
| bge-base-en-v1.5 | 110M | 768 | 512 | 63.55 | 53.25 | 0.21 GB | Yes | MIT |
| bge-large-en-v1.5 | 335M | 1024 | 512 | 64.23 | 54.29 | 1.20 GB | Yes | MIT |
| nomic-embed-text-v1.5 | 137M | 768* | 8192 | 62.28 | ~51.5 | 0.52 GB | Yes | Apache-2.0 |
| bge-m3 | 568M | 1024 | 8192 | N/A† | Strong (MIRACL) | N/A | **No** | MIT |
| jina-embeddings-v3 | 572M | 1024* | 8192 | ~65†† | Strong | N/A | **No** | CC-BY-NC-4.0 |
| pplx-embed-context-v1-0.6B | ~600M | ? | ? | **N/A** | **N/A** | **N/A** | **No** | Gated/Private |

\* Matryoshka: supports 64, 128, 256, 384, 512, 768 dimensions
† bge-m3 is multilingual; its English-only MTEB avg is not directly published but MIRACL/BEIR scores are top-tier
†† jina-v3 self-reported; independent verification limited

**Key observations**:

- bge-large-en-v1.5 gives **+2.06 MTEB points** and **+2.61 retrieval points** over our current baseline — a meaningful improvement
- nomic-embed-text-v1.5 has ~equal MTEB avg to bge-small but trades slight retrieval quality for **16x context window** (8192 vs 512 tokens)
- bge-m3 and jina-v3 are NOT in FastEmbed, requiring a library switch (FlagEmbedding or transformers)
- jina-v3 has CC-BY-NC-4.0 — not compatible with commercial use without license purchase

### 3.3 Reranker Model Comparison

| Model | Params | Language | BEIR NDCG@10 | TREC DL'19 | MS Marco MRR@10 | Size (disk) | FastEmbed | FlagEmbed | License |
|-------|--------|----------|-------------|------------|-----------------|-------------|-----------|-----------|---------|
| bge-reranker-v2-m3 **(current)** | 568M | Multi | 54.17 | — | — | ~2.3 GB | No | Yes | Apache-2.0 |
| ms-marco-MiniLM-L-12-v2 | 33M | EN | — | 74.31 | 39.02 | 0.12 GB | Yes | No | Apache-2.0 |
| jina-reranker-v2-multi | 278M | Multi | 54.83 | — | — | ~1.1 GB | Yes | No | CC-BY-NC-4.0 |

**Key observations**:

- Our current bge-reranker-v2-m3 is already within 0.7 NDCG@10 points of jina-reranker-v2
- ms-marco-MiniLM-L-12-v2 is 17x smaller but English-only and lacks BEIR multi-domain evaluation
- jina-reranker-v2 has the CC-BY-NC-4.0 license restriction
- **The current reranker is already strong; no upgrade justified**

### 3.4 Local Resource Projections (Ryzen 8840U, 16GB RAM)

| Configuration | Embed RAM | Reranker RAM | Total | Embed Throughput† | Rerank 50 Latency† |
|---------------|-----------|-------------|-------|-------------------|---------------------|
| Current: bge-small + bge-reranker-v2-m3 | ~0.13 GB | ~2.3 GB | ~2.4 GB | ~200 chunks/s | ~2-4s |
| **A**: bge-large + bge-reranker-v2-m3 | ~1.2 GB | ~2.3 GB | ~3.5 GB | ~50 chunks/s | ~2-4s |
| **B**: nomic-v1.5 + bge-reranker-v2-m3 | ~0.52 GB | ~2.3 GB | ~2.8 GB | ~100 chunks/s | ~2-4s |
| **C**: bge-m3 (FlagEmbed) + bge-reranker-v2-m3 | ~2.3 GB | ~2.3 GB | ~4.6 GB | ~30 chunks/s | ~2-4s |

† Estimated for 512-token chunks on CPU (ONNX for embed, PyTorch for reranker). Actual throughput depends on batch size and CPU load. bge-reranker-v2-m3 rerank latency is dominated by sequential cross-encoder inference across 50 query-passage pairs.

**All configurations fit within 16GB RAM** (OS + Python overhead ~4-5GB). Options A and B are comfortable; C is tight.

### 3.5 Architecture Flow

```
User Query
    │
    ▼
┌─────────────────────┐
│ Embed(query)        │  ← bi-encoder (ONNX, ~5ms)
│ FastEmbedProvider   │
└─────────┬───────────┘
          │ query vector (384d or 768d or 1024d)
          ▼
┌─────────────────────┐
│ sqlite-vec MATCH    │  ← ANN search (~1ms)
│ top_k * 3 candidates│
└─────────┬───────────┘
          │ candidate IDs + distances
          ▼
┌─────────────────────┐
│ Lookup passage text │  ← chunks/entities/documents table
└─────────┬───────────┘
          │ 50-150 text passages
          ▼
┌─────────────────────┐
│ Reranker.rerank()   │  ← cross-encoder (~2-4s for 50 pairs)
│ BGERerankerProvider │
└─────────┬───────────┘
          │ (index, score) sorted by relevance
          ▼
┌─────────────────────┐
│ Return top_k results│
└─────────────────────┘
```

This is already implemented in `VectorStore._search_with_reranker()` in `vectors.py`. The upgrade only changes which models back the providers.

### 3.6 Failure Mode Analysis for Detail-Oriented Text

**The fundamental problem**: A reranker can only reorder what the retriever fetched. If the embedding model doesn't retrieve a relevant document in the initial candidate set, the reranker can never surface it.

| Failure Mode | Example | Why It Fails | Severity | Mitigation |
|--------------|---------|-------------|----------|------------|
| Exact identifier miss | "ISO 27001:2022 §6.1.2" | Embedding treats "6.1.2" as low-signal tokens; semantically similar clauses rank higher | **High** | BM25 hybrid, metadata filter |
| Policy code lookup | "HR-POL-042" | Opaque code has no semantic content for embeddings | **High** | BM25 hybrid, exact-match pre-filter |
| Numeric precision | "maximum 15 business days" vs "within 20 days" | Embeddings conflate numeric values | **Medium** | Cross-encoder partially helps (token-level attention) |
| Legal cross-reference | "as defined in Section 4.3.1" | Relational references lack standalone semantic meaning | **Medium** | Chunk with context, expand retrieval window |
| Synonym mismatch | "data controller" vs "data processor" (GDPR terms) | Domain-specific terms may be conflated | **Low** | Fine-tuning (long-term), reranker helps short-term |

**Critical insight**: For the ~35% regulatory text in our corpus, dense-only retrieval will have a recall ceiling. The reranker improves precision within the retrieved set but cannot fix recall. **Hybrid retrieval (sparse + dense) is the real fix for identifier-based queries.**

bge-m3 natively supports sparse retrieval (lexical weights) alongside dense, but isn't in FastEmbed. FastEmbed *does* support `Qdrant/bm25` and `prithivida/Splade_PP_en_v1` as sparse models — these could supplement dense retrieval in a separate stage.

### 3.7 Compatibility with Current Architecture

The current codebase has clean protocol abstractions:

- `EmbeddingProvider` protocol in `embeddings.py` — any class with `embed(texts) → list[list[float]]`
- `RerankerProvider` protocol in `reranker.py` — any class with `rerank(query, passages) → list[tuple[int, float]]`
- `VectorStore.search_similar()` in `vectors.py` — already supports optional reranker

**What changes for an embedding model upgrade**:

1. `DEFAULT_MODEL` constant in `embeddings.py` (e.g., `"nomic-ai/nomic-embed-text-v1.5"`)
2. `DEFAULT_DIMENSION` constant (e.g., 768 instead of 384)
3. `EMBEDDING_DIM` in `schema.py` (384 → 768)
4. **Schema migration**: vec0 virtual tables are dimensioned at creation time. Changing dimension requires dropping and recreating `entity_embeddings` and `document_embeddings` tables + re-embedding all stored content
5. `FastEmbedProvider.dimension` property logic

**What does NOT change**: `RerankerProvider`, `BGERerankerProvider`, `VectorStore` API, `search_similar()` signature. The reranker is model-agnostic — it works with any embedding dimension.

## 4. Recommendation

### Embedding Model: nomic-embed-text-v1.5 (.80 confidence)

**Rationale**:

- **8192-token context** is the decisive advantage for regulatory text. ISO clauses, policies, and legal sections often exceed 512 tokens. Currently these get truncated, losing critical content.
- FastEmbed native (ONNX, 0.52 GB) — drop-in replacement for current FastEmbedProvider
- Matryoshka support: can index at 384d for zero-migration testing, then upgrade to 768d
- Apache-2.0 license (commercial-friendly)
- 137M params — 4x larger than current but still comfortable on CPU
- MTEB avg (62.28 at 768d) is comparable to bge-small (62.17 at 384d); the quality gain comes from longer context, not raw benchmark points

**Runner-up**: bge-large-en-v1.5 (.70 confidence) — higher MTEB retrieval score (+2.6 points) but capped at 512 tokens, which doesn't solve the regulatory text truncation problem.

### Reranker Model: Keep bge-reranker-v2-m3 (.85 confidence)

**Rationale**: Already integrated, strong BEIR performance (54.17 NDCG@10), Apache-2.0. No available model offers enough improvement to justify the migration cost.

### Hybrid Retrieval: Add BM25/sparse stage (.75 confidence)

The most impactful improvement for regulatory text isn't a better embedding model — it's adding keyword-based retrieval to catch exact identifiers that dense embeddings miss. FastEmbed supports `Qdrant/bm25` sparse embeddings. This would require a new `SparseVectorStore` or extending the current store with a second index.

## 5. Follow-up Tasks

1. **Upgrade embedding model to nomic-embed-text-v1.5** — Change `DEFAULT_MODEL`, `DEFAULT_DIMENSION`, add schema migration for vec0 dimension change, re-embed all stored content. AC: FastEmbedProvider uses nomic-embed-text-v1.5, tests pass, 768d embeddings stored.

2. **Write schema migration v3→v4 for embedding dimension change** — Drop and recreate vec0 virtual tables with new dimension, preserve bridge table data, trigger re-embedding. AC: `init_db()` migrates existing v3 databases to v4.

3. **Add Matryoshka dimension support to FastEmbedProvider** — Allow configurable output dimension (384, 512, 768) via truncation + renormalization. AC: `FastEmbedProvider(dimension=384)` produces 384d vectors from 768d model.

4. **Investigate BM25/sparse hybrid retrieval for identifier-heavy queries** — Research adding a sparse retrieval stage (FastEmbed `Qdrant/bm25` or `Splade_PP`) that runs alongside dense retrieval, with reciprocal rank fusion to merge results. AC: Research doc with architecture proposal.

5. **Benchmark embedding model upgrade on representative corpus** — Create a test set of 50 queries (mix of semantic, identifier, and cross-reference) against a sample corpus. Measure Recall@50, NDCG@10 before and after model change. AC: Benchmark script in `tests/benchmarks/`, results documented.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| nomic-embed-text-v1.5 | <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5> | Matryoshka embedding model, 8192 tokens, Apache-2.0, MTEB scores | `docs/research/retrieve-rerank.md` (recommendation) | 2026-02-28 |
| BAAI/bge-large-en-v1.5 | <https://huggingface.co/BAAI/bge-large-en-v1.5> | MTEB benchmark scores, model specs | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| BAAI/bge-m3 | <https://huggingface.co/BAAI/bge-m3> | Multi-functionality analysis, sparse retrieval | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| BAAI/bge-reranker-v2-m3 | <https://huggingface.co/BAAI/bge-reranker-v2-m3> | Reranker benchmark, BEIR eval | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| jina-reranker-v2-base-multilingual | <https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual> | Reranker comparison, BEIR/MIRACL benchmarks | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| cross-encoder/ms-marco-MiniLM-L-12-v2 | <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-12-v2> | Lightweight reranker specs, TREC benchmarks | `docs/research/retrieve-rerank.md` (comparison) | 2026-02-28 |
| FastEmbed (Qdrant) | <https://qdrant.github.io/fastembed/examples/Supported_Models/> | ONNX model support list, reranker models | `docs/research/retrieve-rerank.md` (feasibility) | 2026-02-28 |
| SBERT Retrieve & Re-Rank | <https://www.sbert.net/examples/applications/retrieve_rerank/> | Canonical retrieve-and-rerank architecture | `docs/research/retrieve-rerank.md` (prior art) | 2026-02-28 |
| Wang et al. 2024 "Best Practices in RAG" | <https://arxiv.org/abs/2407.01219> | RAG pipeline analysis with reranking | `docs/research/retrieve-rerank.md` (prior art) | 2026-02-28 |
| BGE-M3 paper (Chen et al. 2024) | <https://arxiv.org/abs/2402.03216> | Multi-functionality embedding analysis | `docs/research/retrieve-rerank.md` (analysis) | 2026-02-28 |
