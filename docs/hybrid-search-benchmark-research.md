# Hybrid Search Benchmark Design — nDCG@10 Evaluation

> **Owning task:** #252 — Benchmark hybrid search quality
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

OwlBear migrated from bge-small (384d, dense-only, sqlite-vec) to bge-m3 (1024d, dense+sparse+ColBERT, Qdrant). The claim: hybrid search improves retrieval quality. **Question:** How to measure this empirically? What corpus, queries, metrics, and baselines?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| BEIR benchmark (Thakur et al. 2021) | github.com/beir-cellar/beir | .95 | Standard IR benchmark with 17 datasets + ground truth qrels |
| ranx evaluation library | github.com/AmenRa/ranx | .95 | Fast nDCG/MRR/precision computation with statistical tests |
| Qdrant hybrid search workshop | github.com/qdrant/workshop-ultimate-hybrid-search | .90 | SciFact + ranx evaluation pattern for hybrid search comparison |
| Qdrant "Hybrid Search Revamped" article | qdrant.tech/articles/hybrid-search/ | .90 | ranx + Qrels/Run pattern, fusion vs reranking evaluation |
| bge-m3 paper (Chen et al. 2024) | arxiv.org/abs/2402.03216 | .90 | MIRACL/MLDR benchmark tables for dense vs sparse vs hybrid |
| NFCorpus (BEIR) | huggingface.co/datasets/BeIR/nfcorpus | .85 | 3.6K docs, 323 queries, multi-level relevance — ideal for CPU |
| SciFact (BEIR) | huggingface.co/datasets/BeIR/scifact | .85 | 5K docs, 300 queries, scientific fact-checking |
| OwlBear qdrant-local-research | docs/qdrant-local-research.md | .85 | Current hybrid search implementation details |
| OwlBear colbert-vs-crossencoder-research | docs/colbert-vs-crossencoder-research.md | .85 | Quality comparison tables from bge-m3 paper |

## 3. Analysis

### 3.1 Ground Truth Problem — Solved by BEIR

Measuring nDCG@10 requires ground truth relevance labels (qrels). Two approaches:

| Approach | Pros | Cons | Fit |
|----------|------|------|-----|
| **BEIR datasets** (NFCorpus, SciFact) | Pre-labeled, standard, reproducible, multi-level relevance | Not OwlBear's domain | **.90** — primary |
| **Manual labeling on OwlBear docs** | Domain-specific signal | Subjective, time-consuming, small scale, not reproducible | **.40** — optional |

**Decision:** Use BEIR datasets for quantitative nDCG@10. OwlBear's own docs for latency and qualitative spot-checks only. No manual labeling (YAGNI).

### 3.2 Dataset Selection

| Dataset | Docs | Queries | Avg relevance/query | Download | Why |
|---------|------|---------|---------------------|----------|-----|
| **NFCorpus** | 3,633 | 323 (test) | 38.2 | ~3 MB | Bio-medical. Multi-level relevance (0/1/2). Mixed lexical+semantic. Small = fast on CPU. |
| **SciFact** | 5,183 | 300 (test) | 1.1 | ~4 MB | Scientific fact-checking. Binary relevance. Very clean. Used in Qdrant's own workshop. |

Both fit in memory. bge-m3 embedding of ~5K docs takes ~10-15 min on CPU (batch_size=16). NFCorpus is preferred as primary because its multi-level relevance (scores 0/1/2) makes nDCG more discriminating than binary SciFact.

### 3.3 Evaluation Metrics

| Metric | Formula | What it measures |
|--------|---------|------------------|
| **nDCG@10** | $\text{DCG}@k / \text{IDCG}@k$ where $\text{DCG}@k = \sum_{i=1}^{k}\frac{2^{rel_i}-1}{\log_2(i+1)}$ | Ranking quality with graded relevance |
| **Precision@10** | Relevant docs in top-10 / 10 | Keyword precision |
| **MRR** | $\frac{1}{\lvert Q\rvert}\sum_{i=1}^{\lvert Q\rvert}\frac{1}{\text{rank}_i}$ | Position of first relevant result |
| **Recall@100** | Relevant docs in top-100 / total relevant | Coverage of the retrieval stage |

`ranx` computes all of these from `Qrels` + `Run` objects in one call.

### 3.4 Search Modes to Compare

| Mode | Description | What it tests |
|------|-------------|---------------|
| **dense-only** | bge-m3 1024d dense vectors, cosine search | Semantic retrieval baseline |
| **sparse-only** | bge-m3 lexical weights, sparse search | Keyword/lexical retrieval |
| **hybrid (RRF)** | dense + sparse prefetch → RRF fusion | Classic hybrid search |
| **hybrid+ColBERT** | dense + sparse prefetch → ColBERT max_sim rescore | Full 3-stage pipeline |

All modes use the **same model** (bge-m3). This isolates the **search strategy** variable. Comparing bge-small vs bge-m3 is a separate concern (different model, different dimensionality) — optionally added as a 5th baseline.

### 3.5 Benchmark Script Design

```text
tests/benchmarks/
├── bench_hybrid_search.py      # Main benchmark script
├── conftest.py                 # Shared fixtures (corpus loading, embedding)
└── README.md                   # How to run, interpret results
```

**Architecture:** The script loads BEIR data, embeds all documents with bge-m3 (one pass = dense+sparse+ColBERT), stores in Qdrant `:memory:`, runs all queries in each mode, collects `Run` objects, evaluates with `ranx`.

**Key design choices:**

1. **Single embedding pass** — bge-m3 `embed_hybrid()` produces all 3 vector types. Embed once, query in 4 modes.
2. **ranx for evaluation** — `ranx.evaluate(qrels, run, ["ndcg@10", "precision@10", "mrr"])` per mode.
3. **ranx.compare()** — Statistical significance via paired t-test across all modes.
4. **Latency** — `time.perf_counter()` around each query, mean/p95/p99 per mode.
5. **No real model in CI** — Benchmark is `@pytest.mark.benchmark` (or standalone script), skipped in normal test runs. Mock-based unit tests for the harness itself.

### 3.6 Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| `beir` | Load NFCorpus/SciFact datasets | `uv pip install beir` |
| `ranx` | nDCG/MRR/precision computation | `uv pip install ranx` |
| `qdrant-client` | Vector store (already installed) | — |
| `FlagEmbedding` | bge-m3 embeddings (already installed) | — |

`beir` and `ranx` are benchmark-only deps. Add as optional extras: `uv pip install 'owlbear[benchmark]'`.

### 3.7 Expected Results (from bge-m3 paper benchmarks)

From Chen et al. 2024 (MIRACL-18 languages), translated to our modes:

| Mode | Expected nDCG@10 (MIRACL) | Delta vs dense |
|------|--------------------------|----------------|
| Dense-only | ~69.2 | baseline |
| Sparse-only | ~53.9 | -15.3 |
| Hybrid (dense+sparse) | ~70.4 | +1.2 |
| Hybrid+ColBERT | ~71.5 | +2.3 |

On NFCorpus specifically, expect smaller absolute values but same relative ordering. The benchmark validates whether our Qdrant pipeline reproduces these gains.

## 4. Recommendation (.85 confidence)

**Use BEIR NFCorpus + ranx + 4-mode comparison.** This is the approach Qdrant's own workshop uses (SciFact + ranx). NFCorpus preferred over SciFact for multi-level relevance.

**Script structure:**

1. Load BEIR dataset via `beir.datasets`
2. Embed corpus with `BgeM3EmbeddingProvider.embed_hybrid()`
3. Store all vectors in `QdrantVectorStore(:memory:)`
4. For each query × mode: search, collect (doc_id, score) pairs → `ranx.Run`
5. `ranx.compare(qrels, [dense_run, sparse_run, hybrid_run, colbert_run], ["ndcg@10", "precision@10", "mrr"])` → comparison table with statistical significance
6. Measure and report latency per mode

**Risks:**

- bge-m3 embedding of 3.6K docs takes ~10 min on CPU — acceptable for a benchmark, not for CI
- ranx + beir add ~50 MB of dependencies — benchmark-only extras
- NFCorpus is bio-medical, not OwlBear's domain — but nDCG is relative (comparing modes, not absolute quality)

## 5. Follow-up Tasks

1. **Add benchmark optional extras to pyproject.toml** — Add `[benchmark]` extras group with `beir`, `ranx`. Keep out of default install. Priority: needed. Tags: phase-9, test, config. AC: `uv pip install -e '.[benchmark]'` installs beir + ranx.

2. **Create benchmark corpus loader** — `tests/benchmarks/conftest.py` with fixtures that load NFCorpus via BEIR, cache locally. Priority: needed. Tags: phase-9, test, knowledge-graph. AC: `load_nfcorpus()` returns corpus dict, queries dict, qrels dict. Depends: 1.

3. **Create benchmark embedding + indexing** — Embed NFCorpus with bge-m3, store in Qdrant `:memory:`. Cache embeddings to disk (pickle/parquet) to avoid re-computing on every run. Priority: needed. Tags: phase-9, test, embedding. AC: All 3.6K docs embedded with dense+sparse+ColBERT vectors in Qdrant. Depends: 2.

4. **Implement 4-mode search harness** — Run all queries in dense-only, sparse-only, hybrid-RRF, hybrid+ColBERT modes. Build `ranx.Run` per mode. Priority: needed. Tags: phase-9, test, knowledge-graph. AC: 4 `Run` objects with (query_id → {doc_id: score}) for all 323 queries. Depends: 3.

5. **Evaluate and report results** — `ranx.compare()` for nDCG@10, precision@10, MRR with statistical tests. Latency table (mean/p95/p99). Output to console + `docs/hybrid-search-benchmark-results.md`. Priority: needed. Tags: phase-9, test, docs. AC: Results table with statistical significance, latency table, documented findings. Depends: 4.

6. **Unit tests for benchmark harness** — TDD tests for corpus loading, run building, evaluation wrappers. Use mocked embeddings (no real model). `@pytest.mark.benchmark` skipped in normal runs. Priority: important. Tags: phase-9, test. AC: Tests pass, harness logic verified without loading bge-m3. Depends: 2.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| BEIR benchmark | github.com/beir-cellar/beir | Standard IR benchmark with ground truth qrels | docs/hybrid-search-benchmark-research.md | 2026-03-01 |
| ranx | github.com/AmenRa/ranx | IR evaluation library (nDCG, MRR, precision, statistical tests) | docs/hybrid-search-benchmark-research.md | 2026-03-01 |
| Qdrant hybrid search workshop | github.com/qdrant/workshop-ultimate-hybrid-search | SciFact + ranx evaluation pattern | docs/hybrid-search-benchmark-research.md | 2026-03-01 |
| Qdrant hybrid search article | qdrant.tech/articles/hybrid-search/ | ranx + Qrels/Run evaluation methodology | docs/hybrid-search-benchmark-research.md | 2026-03-01 |
| NFCorpus (BEIR) | huggingface.co/datasets/BeIR/nfcorpus | 3.6K doc bio-medical IR dataset with multi-level relevance | docs/hybrid-search-benchmark-research.md | 2026-03-01 |
