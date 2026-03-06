---
id: 478
title: 'Fix TestLoadNfcorpus: add skip guard for network failures'
status: archived
priority: needed
created: 2026-03-04T07:37:56.6489322+01:00
updated: 2026-03-06T19:28:26.1181309+01:00
started: 2026-03-06T16:41:22.0169185+01:00
completed: 2026-03-06T19:28:26.1181309+01:00
tags:
    - audit
    - test
class: standard
---

## Acceptance Criteria

- [ ] `TestLoadNfcorpus` tests in `tests/test_benchmark_harness.py` skip gracefully (`pytest.skip()`) when `load_nfcorpus()` raises a network error (`ConnectionError`, `OSError`, `requests.exceptions.RequestException`)
- [ ] `nfcorpus` session fixture in `tests/benchmarks/conftest.py` has matching skip guard
- [ ] Existing `@pytest.mark.api` and `@pytest.mark.benchmark` markers preserved (no new markers)
- [ ] Tests still run and pass when network IS available (or cache at `tests/benchmarks/.cache/nfcorpus/` is populated)
- [ ] `uv run pytest -m 'not api' -q --tb=short` runs clean (these tests excluded by existing marker)
- [ ] `uv run pytest tests/test_benchmark_harness.py::TestLoadNfcorpus -q` either passes (network+cache) or all 6 tests skip (network unavailable)
- [ ] No new dependencies added

## Implementation Notes

- Wrap `load_nfcorpus()` calls in `try/except` catching `(ConnectionError, OSError)` and `requests.exceptions.RequestException`  call `pytest.skip('NFCorpus download unavailable: {exc}')`  
- 2 files: `tests/test_benchmark_harness.py` (guard in each of the 6 test methods or a class-level fixture) and `tests/benchmarks/conftest.py` (guard the session fixture)
- Research chose Option A (.85)  skip guard only, no new marker (KISS)

## Research

See original research findings below and docs/test-quality-audit.md for context.
