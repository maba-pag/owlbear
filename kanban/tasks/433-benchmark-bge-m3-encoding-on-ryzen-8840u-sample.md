---
id: 433
title: Benchmark bge-m3 encoding on Ryzen 8840U sample corpus
status: archived
priority: important
created: 2026-03-03T16:18:56.9973416+01:00
updated: 2026-03-04T07:58:15.1050813+01:00
started: 2026-03-03T19:08:39.6806289+01:00
completed: 2026-03-04T07:58:15.1050813+01:00
tags:
    - phase-10
    - test
    - embedding
class: standard
---

Measure actual RAM and latency for `BgeM3EmbeddingProvider` on Ryzen 8840U.

Preconditions:
- FlagEmbedding installed (`knowledge` extra)
- psutil available (add to `benchmark` extra in pyproject.toml)

AC:

1. **Script location:** `tests/benchmarks/bench_encoding.py` following existing bench pattern (`@pytest.mark.benchmark`, standalone `__main__` block).
2. **Corpus:** Generate 128 synthetic chunks of ~200 tokens each (deterministic seed, lorem-style technical text). No network dependency.
3. **Batch sizes tested:** 4, 8, 16, 32 — instantiate `BgeM3EmbeddingProvider(batch_size=N)` for each.
4. **Modes tested:** `embed()` (dense-only) and `embed_hybrid()` (dense + sparse + ColBERT) for each batch size.
5. **Metrics recorded per (batch_size, mode) combination:**
   - Peak RSS delta (bytes): `psutil.Process(os.getpid()).memory_info().rss` sampled before model load, after model load, and after encoding. Report max delta.
   - Encoding throughput: chunks/sec (wall-clock, exclude model load time).
   - Model load time (seconds): time from `_ensure_model()` start to first encode call.
6. **Output:** Print formatted table to stdout. Write results to `docs/bge-m3-encoding-benchmark-results.md` with hardware info header (CPU, RAM, OS, Python version, FlagEmbedding version).
7. **Cleanup:** Call `provider.unload()` between batch-size runs to reset RSS baseline.
8. **Add `psutil` to `benchmark` extra** in pyproject.toml.

Patterns to follow:
- `bench_graph_expansion.py` for structure and pytest marker
- `bench_hybrid_search.py` for results-doc writing pattern
- `BgeM3EmbeddingProvider` constructor for batch_size param
- `embed()` for dense-only, `embed_hybrid()` for all-three

Not in scope: search/retrieval quality, Qdrant indexing, query latency (covered by #380).
