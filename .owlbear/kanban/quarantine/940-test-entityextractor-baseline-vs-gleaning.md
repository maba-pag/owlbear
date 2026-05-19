---
id: 940
title: Test EntityExtractor baseline-vs-gleaning benchmark runner
status: archived
priority: nice-to-have
created: 2026-03-22T17:07:35.5756273+01:00
updated: 2026-03-22T17:07:35.5756273+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - test
    - type:test
    - phase-research
parent: 908
depends_on:
    - 906
    - 907
class: standard
---

AC: add focused failing tests in tests/benchmarks/ that prove the baseline-vs-gleaning runner uses the same #906 gold corpus and scorer for both variants, reports side-by-side micro recall and per-type recall plus token/cost and elapsed-time deltas, and stays opt-in behind the existing benchmark/api markers or an equivalent explicit benchmark entry point. Paired GREEN task: #915. Affected files: tests/benchmarks/, src/owlbear/memory/knowledge/extractor.py, src/owlbear/memory/usage.py.
