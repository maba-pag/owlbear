---
id: 454
title: Mark NFCorpus download tests with @pytest.mark.api
status: archived
priority: needed
created: 2026-03-03T18:59:52.4119114+01:00
updated: 2026-03-04T07:58:28.6337303+01:00
started: 2026-03-03T19:08:38.9621495+01:00
completed: 2026-03-04T07:58:28.6337303+01:00
tags:
    - test
    - phase-refactor
class: standard
---

## Problem
All 6 TestLoadNfcorpus tests in tests/test_benchmark_harness.py fail on default runs due to SSL certificate verification errors (corporate proxy / self-signed CA). These tests download the NFCorpus dataset from public.ukp.informatik.tu-darmstadt.de and require network access.

## Acceptance Criteria
- [ ] All 6 TestLoadNfcorpus tests are decorated with @pytest.mark.api
- [ ] uv run pytest tests/ -m 'not api' -q --tb=short passes with 0 failures from this class
- [ ] Tests still runnable when explicitly included: uv run pytest tests/test_benchmark_harness.py -m api

## Affected tests
- test_returns_three_tuple
- test_corpus_is_dict_str_str
- test_queries_is_dict_str_str
- test_qrels_structure
- test_qrels_query_ids_subset_of_queries
- test_qrels_doc_ids_subset_of_corpus
