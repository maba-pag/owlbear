---
id: 377
title: Benchmark corpus loader — NFCorpus via BEIR
status: archived
priority: needed
created: 2026-03-01T20:14:09.4041236+01:00
updated: 2026-03-02T09:17:00.8412125+01:00
started: 2026-03-01T20:22:49.273547+01:00
completed: 2026-03-02T09:17:00.8412125+01:00
tags:
    - phase-9
    - test
    - knowledge-graph
depends_on:
    - 376
    - 381
class: standard
---

From docs/research/hybrid-search-benchmark.md §3.2 and §5.2.

## Acceptance Criteria

- [ ] `tests/benchmarks/conftest.py` with shared fixtures for the benchmark suite
- [ ] `load_nfcorpus()` fixture/function returns 3-tuple:
  - `corpus: dict[str, str]` — doc_id to text (3,633 docs)
  - `queries: dict[str, str]` — query_id to text (323 test queries)
  - `qrels: dict[str, dict[str, int]]` — query_id to {doc_id: relevance} (levels 0/1/2)
- [ ] Data cached to `tests/benchmarks/.cache/nfcorpus/` after first download
- [ ] Subsequent calls load from cache without network access
- [ ] Uses `beir` library for dataset download (from [benchmark] extras group)
- [ ] `build_qrels()` utility converts raw qrels dict to `ranx.Qrels` object
- [ ] `@pytest.mark.benchmark` on all fixtures/functions that touch real data or disk
- [ ] Makes corresponding corpus-loading tests in #381 pass
- [ ] ruff clean

## Patterns to follow

- BEIR dataset loading: `from beir.datasets.data_loader import GenericDataLoader`
- Existing conftest.py fixtures at tests/conftest.py (monkeypatch, settings)

## Notes

- NFCorpus chosen for multi-level relevance (0/1/2) — more discriminating nDCG than binary SciFact.
- ~3 MB download, cached after first run.
