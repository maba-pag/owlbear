# Embedding Model Shootout — Local Feasibility & Honest Benchmarks

> **Owning task:** #235 — Research: Embedding model shootout
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge pipeline serves a mixed-domain corpus: ~35% ISO norms/policies/laws (identifier-heavy), ~50% technical docs (code, APIs), ~15% general info. Current stack: `BAAI/bge-small-en-v1.5` (33M, 384d, 512 tokens) via FastEmbed ONNX + optional bge-reranker-v2-m3. Task #232 recommends adding SPLADE++ sparse embeddings with RRF.

**Question:** Which dense embedding model is the best upgrade for the dense component, given local hardware (Ryzen 8840U, 16GB RAM, no GPU)?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| FastEmbed supported models | qdrant.github.io/fastembed/examples/Supported_Models | .95 | Complete ONNX model inventory with sizes |
| MTEB leaderboard | huggingface.co/spaces/mteb/leaderboard | .95 | Third-party benchmark scores |
| mxbai-embed-large-v1 model card | huggingface.co/mixedbread-ai/mxbai-embed-large-v1 | .90 | MTEB scores, Matryoshka + binary quantization support |
| gte-large-en-v1.5 model card | huggingface.co/Alibaba-NLP/gte-large-en-v1.5 | .85 | 8192 tokens, MTEB/LoCo benchmarks, custom architecture |
| snowflake-arctic-embed-l model card | huggingface.co/Snowflake/snowflake-arctic-embed-l | .90 | BEIR retrieval-optimized, comparison tables |
| nomic-embed-text-v1.5 model card | huggingface.co/nomic-ai/nomic-embed-text-v1.5 | .90 | Matryoshka dims, 8192 context, Apache-2.0 |
| jina-embeddings-v3 model card | huggingface.co/jinaai/jina-embeddings-v3 | .70 | 0.6B params, CC-BY-NC-4.0 — license disqualifies |
| e5-mistral-7b-instruct model card | huggingface.co/intfloat/e5-mistral-7b-instruct | .60 | 7B reference model, MIT, infeasible on 16GB |
| pplx-embed-context-v1 (0.6B + 4B) | huggingface.co/pplx/ | .95 | **HTTP 401 on both** — gated, no MTEB submission |
| OwlBear dual-embedding-rrf-research | docs/dual-embedding-rrf-research.md | .90 | Current pipeline design, SPLADE++ pairing |
| OwlBear retrieve-rerank-research | docs/retrieve-rerank-research.md | .85 | Reranker comparison, local feasibility data |

## 3. Analysis

### 3.1 Disqualified Models

| Model | Reason | Status |
|-------|--------|--------|
| **pplx-embed-context-v1-0.6B** | HTTP 401 — weights gated/private. No independent MTEB submission. "5-10x improvement" claim **unverifiable**. | **DISQUALIFIED** |
| **pplx-embed-context-v1-4B** | HTTP 401 — same as above. Even if accessible, 4B params ≈ 8GB+ RAM. | **DISQUALIFIED** |
| **e5-mistral-7b-instruct** | 7B params, 4096d. FP16 ≈ 14GB — exceeds 16GB budget (OS+Python take ~4-5GB). No ONNX. | **INFEASIBLE** |
| **jina-embeddings-v3** | 0.6B params, strong benchmarks, 8192 tokens. **CC-BY-NC-4.0 license** — non-commercial only. Not in FastEmbed. Requires `trust_remote_code=True`. | **LICENSE BLOCKED** |
| **bge-m3** | 568M, dense+sparse+ColBERT. Not in FastEmbed — requires FlagEmbedding (PyTorch ~2GB dep). Better as future Qdrant upgrade path (task #236). | **DEFERRED** (not disqualified) |
| **gte-large-en-v1.5** | 409M, 1024d, 8192 tokens. Strong retrieval (57.91). Not in FastEmbed — custom arch requires `trust_remote_code=True`. No ONNX export. | **DEFERRED** (not disqualified) |

### 3.2 Dense Embedding Model Comparison — FastEmbed Viable (ONNX)

All scores from MTEB leaderboard submissions or model card self-reports cross-validated with Snowflake's comparison tables. Retrieval = BEIR nDCG@10 average.

| Model | Params | Dim | Tokens | MTEB Avg | Retrieval | ONNX (GB) | RAM (est.) | Matryoshka | License |
|-------|--------|-----|--------|----------|-----------|-----------|------------|------------|---------|
| bge-small-en-v1.5 **(current)** | 33M | 384 | 512 | 62.17 | 51.68 | 0.07 | ~80 MB | No | MIT |
| snowflake-arctic-embed-s | 33M | 384 | 512 | — | 51.98 | 0.13 | ~100 MB | No | Apache-2.0 |
| bge-base-en-v1.5 | 110M | 768 | 512 | 63.55 | 53.25 | 0.21 | ~200 MB | No | MIT |
| snowflake-arctic-embed-m | 110M | 768 | 512 | — | 54.90 | 0.43 | ~350 MB | No | Apache-2.0 |
| nomic-embed-text-v1.5 | 137M | 768 | 8192 | 62.28 | 53.25 | 0.52 | ~500 MB | Yes (64–768) | Apache-2.0 |
| **mxbai-embed-large-v1** | 335M | 1024 | 512 | **64.68** | 54.39 | 0.64 | ~700 MB | Yes | Apache-2.0 |
| **snowflake-arctic-embed-l** | 335M | 1024 | 512 | — | **55.98** | 1.02 | ~1.0 GB | No | Apache-2.0 |
| bge-large-en-v1.5 | 335M | 1024 | 512 | 64.23 | 54.29 | 1.20 | ~1.1 GB | No | MIT |

**Key observations:**

1. **snowflake-arctic-embed-l has the best retrieval score** (55.98) among all FastEmbed models — +4.3 points over current baseline. Purpose-built for retrieval.
2. **mxbai-embed-large-v1 has the best overall MTEB average** (64.68) and strong retrieval (54.39). Supports Matryoshka + binary quantization.
3. **nomic-embed-text-v1.5** is the only 8192-token model in FastEmbed. Retrieval (53.25) is modest — equal to bge-base which is smaller.
4. **snowflake-arctic-embed-m** at 110M params delivers 54.90 retrieval — better than all 137M+ models except snowflake-l and mxbai. Best quality/size ratio.
5. The 8192-token context of nomic is **less relevant than it appears**: our chunker produces 512-token chunks. Long context helps only if we increase chunk size.

### 3.3 Non-FastEmbed Models (Feasible but Heavier)

| Model | Params | Dim | Tokens | Retrieval | RAM (est.) | Dependency | Why deferred |
|-------|--------|-----|--------|-----------|------------|------------|-------------|
| gte-large-en-v1.5 | 409M | 1024 | 8192 | **57.91** | ~2.0 GB | transformers+custom_code | No ONNX/FastEmbed; best retrieval of any feasible model |
| bge-m3 (dense) | 568M | 1024 | 8192 | ~56.2 | ~3.0 GB | FlagEmbedding+PyTorch | Also outputs sparse+ColBERT; awaits Qdrant migration (#236) |

### 3.4 Reranker Models

Prior research (#231) concluded: **keep bge-reranker-v2-m3** (.85 confidence). For completeness, here are FastEmbed ONNX rerankers that could eliminate the PyTorch dependency:

| Model | Size (ONNX) | Domain | Notes | License |
|-------|-------------|--------|-------|---------|
| Xenova/ms-marco-MiniLM-L-6-v2 | 0.08 GB | EN | Blazing fast, lower quality | Apache-2.0 |
| Xenova/ms-marco-MiniLM-L-12-v2 | 0.12 GB | EN | Good MS Marco scores | Apache-2.0 |
| jinaai/jina-reranker-v1-tiny-en | 0.13 GB | EN | 8K context | Apache-2.0 |
| jinaai/jina-reranker-v1-turbo-en | 0.15 GB | EN | 8K context | Apache-2.0 |
| BAAI/bge-reranker-base | 1.04 GB | Multi | Solid baseline | MIT |
| jinaai/jina-reranker-v2-base-multi | 1.11 GB | Multi | CC-BY-NC-4.0 — **license blocked** | CC-BY-NC-4.0 |

If we want a **fully ONNX/FastEmbed stack** (no PyTorch): BAAI/bge-reranker-base (1.04 GB ONNX) is the best option. Lower than bge-reranker-v2-m3 quality but eliminates the PyTorch dependency.

### 3.5 Local Feasibility — Ryzen 8840U / 16 GB RAM

Budget: ~11 GB available (16 GB - ~5 GB OS/Python/IDE).

| Configuration | Dense ONNX | Sparse ONNX | Reranker | Total RAM | Throughput (est.) | Fits? |
|---------------|------------|-------------|----------|-----------|-------------------|-------|
| Current: bge-small + reranker (PyTorch) | 80 MB | — | ~2.3 GB | ~2.4 GB | ~200 ch/s | ✅ |
| **A:** snowflake-arctic-l + SPLADE++ | 1.0 GB | 700 MB | — | ~1.7 GB | ~60 ch/s | ✅✅ |
| **A+:** + bge-reranker-base (ONNX) | 1.0 GB | 700 MB | 1.0 GB | ~2.7 GB | ~50 ch/s | ✅✅ |
| **B:** mxbai-embed-large + SPLADE++ | 700 MB | 700 MB | — | ~1.4 GB | ~70 ch/s | ✅✅ |
| **C:** snowflake-arctic-m + SPLADE++ | 350 MB | 700 MB | — | ~1.1 GB | ~100 ch/s | ✅✅✅ |
| **D:** nomic-v1.5 + SPLADE++ | 500 MB | 700 MB | — | ~1.2 GB | ~80 ch/s | ✅✅ |
| **E:** gte-large-v1.5 (PyTorch) + SPLADE++ | 2.0 GB | 700 MB | — | ~2.7 GB | ~25 ch/s | ✅ |

**Can two models run in parallel?** Yes — all ONNX configurations easily fit. Even adding a reranker stays well under 11 GB. Two 0.6B PyTorch models would be tight (~6 GB) but feasible.

### 3.6 Matryoshka (Variable Dimension) Support

| Model | Supported Dims | Quality at 384d (vs full) | Notes |
|-------|---------------|--------------------------|-------|
| nomic-embed-text-v1.5 | 64, 128, 256, 512, 768 | 61.04 MTEB at 256d (vs 62.28 full) | Best Matryoshka implementation |
| mxbai-embed-large-v1 | Truncation to any dim | ~62.5 at 512d (est. from blog) | Also supports binary quantization |
| bge-small (current) | No | N/A | Fixed 384d |
| snowflake-arctic-embed-l | No | N/A | Fixed 1024d |

Matryoshka is useful for flexible storage — start at 384d (zero-migration A/B test against current baseline), then upgrade to higher dims.

### 3.7 Answering the Research Questions

**Q1: Best single model for local hardware?**
**snowflake-arctic-embed-l** (.80 confidence) — highest retrieval score (55.98) of any FastEmbed model. +4.3 points over current baseline. Fits comfortably (1.0 GB ONNX).

**Q2: Best pair for dual-embedding (semantic + lexical)?**
**snowflake-arctic-embed-l (dense) + SPLADE++ (sparse)** via FastEmbed (.80 confidence) — total ~1.7 GB RAM. As designed in #232.

**Q3: Is a 4B model feasible on 16GB?**
**No.** pplx-embed-context-v1-4B weights aren't even downloadable. A generic 4B model at FP16 = ~8 GB RAM, leaving only ~3 GB for OS + sparse model + reranker. Not practical.

**Q4: Which models support Matryoshka?**
nomic-embed-text-v1.5 (64–768) and mxbai-embed-large-v1 (any truncation). Matryoshka enables zero-migration testing at 384d before committing to higher dims.

**Q5: Realistic quality gap between current and best feasible?**
bge-small retrieval: 51.68 → snowflake-arctic-embed-l: 55.98 = **+4.30 points**. This is meaningful — comparable to the gap between OpenAI text-embedding-3-large (55.44) and bge-small. For context, snowflake-arctic-embed-l (55.98) beats Google Gecko (55.7) and OpenAI's best (55.44).

## 4. Recommendation

### Primary: snowflake-arctic-embed-l (.80 confidence)

Best retrieval quality in FastEmbed. Purpose-built for retrieval (not general-purpose MTEB). 1024d vectors, 512-token context (fine for our 512-token chunks).

### Runner-up: mxbai-embed-large-v1 (.75 confidence)

Slightly lower retrieval (54.39 vs 55.98) but best overall MTEB average (64.68 — useful beyond retrieval). Matryoshka support enables gradual migration at 384d first. Smaller ONNX file (0.64 vs 1.02 GB).

### Long-context alternative: nomic-embed-text-v1.5 (.60 confidence)

Only pick this if we plan to increase chunk size >512 tokens. At 512-token chunks, the 8192-token context provides no benefit and retrieval (53.25) is worse than both primaries. However, if future chunk size experiments (#232 follow-up) show gains from 1024+ token chunks, nomic becomes the best option.

### Decision tree

```
Do you plan to increase chunk size > 512 tokens?
├─ Yes → nomic-embed-text-v1.5 (8192 tokens, Matryoshka for migration)
└─ No  → Do you value Matryoshka for gradual migration?
         ├─ Yes → mxbai-embed-large-v1 (384d test → 1024d upgrade)
         └─ No  → snowflake-arctic-embed-l (best raw retrieval)
```

### KISS / YAGNI assessment

All three options stay within FastEmbed ONNX — **no new dependencies**. The schema migration from 384d → 1024d is the same effort regardless of model choice. The dual-embedding architecture from #232 is unaffected — only the dense component changes.

## 5. Follow-up Tasks

1. **Upgrade dense embedding model** — Change `DEFAULT_MODEL` to chosen model (snowflake-arctic-l or mxbai-embed-large), update `DEFAULT_DIMENSION` and `EMBEDDING_DIM`, add schema migration v→v+1 for vec0 dimension change. TDD. Priority: needed. Tags: phase-9, embedding, knowledge-graph. Depends on: user decision on model choice.

2. **Add Matryoshka dimension support to FastEmbedProvider** — If mxbai or nomic is chosen: configurable output dim via truncation + renorm. Enables 384d testing before full migration. TDD. Priority: important. Tags: phase-9, embedding. Depends on: task 1.

3. **Benchmark: dense model upgrade on sample corpus** — Create test set of ~50 queries against sample corpus (ISO clauses, code docs, slides). Measure Recall@10 and nDCG@10 before/after model change. Priority: important. Tags: phase-9, test, knowledge-graph. Depends on: task 1.

4. **Evaluate ONNX reranker to eliminate PyTorch dep** — If KISS-purism prevails: benchmark bge-reranker-base ONNX (via FastEmbed `TextCrossEncoder`) against current bge-reranker-v2-m3 (PyTorch). If quality gap < 2 nDCG@10 points, switch. Priority: nice-to-have. Tags: phase-9, embedding.

5. **Chunk-size experiment with 8192-token model** — Test nomic-embed-text-v1.5 at 1024-token and 2048-token chunk sizes on normative text subset. See if longer chunks improve retrieval for regulatory documents. Priority: important. Tags: phase-9, knowledge-graph, research. Depends on: task 3.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| snowflake-arctic-embed-l | huggingface.co/Snowflake/snowflake-arctic-embed-l | BEIR retrieval benchmarks, model specs, comparison tables | docs/embedding-model-shootout.md | 2026-02-28 |
| mxbai-embed-large-v1 | huggingface.co/mixedbread-ai/mxbai-embed-large-v1 | MTEB scores, Matryoshka + binary quantization details | docs/embedding-model-shootout.md | 2026-02-28 |
| gte-large-en-v1.5 | huggingface.co/Alibaba-NLP/gte-large-en-v1.5 | MTEB/LoCo benchmarks, 8192-token retrieval scores | docs/embedding-model-shootout.md | 2026-02-28 |
| nomic-embed-text-v1.5 | huggingface.co/nomic-ai/nomic-embed-text-v1.5 | Matryoshka dimension table, 8192 context, MTEB scores | docs/embedding-model-shootout.md | 2026-02-28 |
| jina-embeddings-v3 | huggingface.co/jinaai/jina-embeddings-v3 | CC-BY-NC-4.0 license confirmation, 0.6B params | docs/embedding-model-shootout.md | 2026-02-28 |
| e5-mistral-7b-instruct | huggingface.co/intfloat/e5-mistral-7b-instruct | 7B params, 4096d, MIT license, infeasibility assessment | docs/embedding-model-shootout.md | 2026-02-28 |
| FastEmbed supported models | qdrant.github.io/fastembed/examples/Supported_Models | Complete ONNX model + reranker inventory with sizes | docs/embedding-model-shootout.md | 2026-02-28 |
| pplx-embed-context-v1 (0.6B + 4B) | huggingface.co/pplx/ | HTTP 401 confirmation — weights not publicly accessible | docs/embedding-model-shootout.md | 2026-02-28 |
