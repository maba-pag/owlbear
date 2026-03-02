---
id: 379
title: 4-mode search harness — dense, sparse, hybrid-RRF, hybrid+ColBERT
status: archived
priority: needed
created: 2026-03-01T20:14:28.7328833+01:00
updated: 2026-03-02T09:17:04.843858+01:00
started: 2026-03-01T20:22:52.1162192+01:00
completed: 2026-03-02T09:17:04.843858+01:00
tags:
    - phase-9
    - test
    - knowledge-graph
depends_on:
    - 378
class: standard
---

From docs/hybrid-search-benchmark-research.md §3.4 and §5.4.

## Acceptance Criteria

- [ ] Function in `tests/benchmarks/` that runs all 323 NFCorpus queries in 4 modes
- [ ] Mode 1 — dense-only: query with dense vector only via `QdrantVectorStore`
- [ ] Mode 2 — sparse-only: query with sparse vector only via `QdrantVectorStore`
- [ ] Mode 3 — hybrid-RRF: query with `HybridEmbedding(dense, sparse)` — dense+sparse prefetch with RRF fusion
- [ ] Mode 4 — hybrid+ColBERT: query with `HybridEmbedding(dense, sparse, colbert)` — full 3-stage pipeline with ColBERT rescore
- [ ] Each mode produces a `ranx.Run` object: `{query_id: {doc_id: float_score}}`
- [ ] Per-query latency recorded via `time.perf_counter()` — stored as `{mode_name: list[float]}`
- [ ] All 4 modes isolated — each queries the same pre-populated Qdrant collection independently
- [ ] Returns `(runs: dict[str, ranx.Run], latencies: dict[str, list[float]])`
- [ ] Makes corresponding run-building tests in #381 pass
- [ ] `@pytest.mark.benchmark` marker
- [ ] ruff clean

## Patterns to follow

- `QdrantVectorStore.search_similar()` (qdrant.py) — dense path and hybrid path
- `QdrantVectorStore._dense_search()` / `_hybrid_search()` for mode differences
- Query embedding: `BgeM3EmbeddingProvider.embed_hybrid()` — one pass per query

## Notes

- All 4 modes use same bge-m3 model — isolates search STRATEGY variable.
- Dense-only and sparse-only require manual construction of query (skip hybrid path).
