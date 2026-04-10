---
id: 381
title: Unit tests for benchmark harness (mocked, no real model)
status: archived
priority: important
created: 2026-03-01T20:14:46.3111755+01:00
updated: 2026-03-02T09:14:43.1624846+01:00
started: 2026-03-01T20:22:55.4968101+01:00
completed: 2026-03-02T09:14:43.1624846+01:00
tags:
    - phase-9
    - test
depends_on:
    - 376
class: standard
---

TDD test task for benchmark harness utilities (#377-380). Write tests BEFORE implementations.

From docs/research/hybrid-search-benchmark.md §3.5 (design) and §5.6 (follow-up).

## Acceptance Criteria

- [ ] `tests/test_benchmark_harness.py` with unit tests for harness utilities
- [ ] Test corpus loading: `load_nfcorpus()` returns `(corpus: dict[str, str], queries: dict[str, str], qrels: dict[str, dict[str, int]])` — mock BEIR download, verify structure and types
- [ ] Test Qrels conversion: `build_qrels(qrels_dict)` constructs a valid `ranx.Qrels` object from raw dict
- [ ] Test Run building: `build_run(results: dict[str, dict[str, float]])` constructs a valid `ranx.Run` object
- [ ] Test latency recording: verify per-query timing dict structure `{mode: list[float]}`
- [ ] All tests decorated with `@pytest.mark.benchmark` — skipped in default `pytest -m 'not benchmark'` runs
- [ ] No real bge-m3 model loaded — all embeddings replaced with random float vectors
- [ ] No real BEIR data download — corpus/queries/qrels fixtures use small synthetic dicts
- [ ] Tests initially fail (TDD contract: implementations in #377-380 make them pass)
- [ ] ruff clean

## Patterns to follow

- Existing test file structure: `tests/test_*.py` (not in tests/benchmarks/ — unit tests stay at top level)
- Mock patterns: `unittest.mock.patch` / `MagicMock` (see tests/conftest.py)
- `@pytest.mark.slow` pattern adapted for `@pytest.mark.benchmark`

## Notes

- This is a TDD task. Must be completed BEFORE #377, #378, #379, #380.
- Tests define the API contract for harness utility functions.
- Builder writes tests that fail, then implements #377-380 to make them pass.
