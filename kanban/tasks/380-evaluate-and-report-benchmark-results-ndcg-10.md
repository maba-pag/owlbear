---
id: 380
title: Evaluate and report benchmark results — nDCG@10 + latency
status: archived
priority: needed
created: 2026-03-01T20:14:37.6519905+01:00
updated: 2026-03-02T09:17:06.7971832+01:00
started: 2026-03-01T20:22:53.6046773+01:00
completed: 2026-03-02T09:17:06.7971832+01:00
tags:
    - phase-9
    - test
    - docs
depends_on:
    - 379
class: standard
---

From docs/research/hybrid-search-benchmark.md §3.3, §4 (step 5), and §5.5.

## Acceptance Criteria

- [ ] `ranx.compare(qrels, [dense_run, sparse_run, hybrid_run, colbert_run], ['ndcg@10', 'precision@10', 'mrr'])` produces comparison table with statistical significance (paired t-test)
- [ ] Latency table computed from per-query timings: mean, p50, p95, p99 per mode
- [ ] Results printed to console in formatted table (human-readable)
- [ ] Results written to `docs/hybrid-search-benchmark-results.md` with:
  - Comparison table (all metrics x all modes)
  - Latency table
  - Statistical significance indicators
  - Date, corpus name (NFCorpus), model version (bge-m3)
- [ ] Script runnable standalone: `uv run python tests/benchmarks/bench_hybrid_search.py`
- [ ] Makes corresponding evaluation tests in #381 pass
- [ ] `@pytest.mark.benchmark` marker
- [ ] ruff clean

## Patterns to follow

- `ranx.evaluate()` and `ranx.compare()` (per research doc §3.3)
- Existing `docs/*.md` format for research/analysis documents

## Notes

- Expected results from bge-m3 paper: hybrid+ColBERT > hybrid-RRF > dense-only > sparse-only (§3.7).
- Statistical test confirms whether differences are significant or within noise.
