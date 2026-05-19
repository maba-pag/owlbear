---
id: 915
title: Build EntityExtractor baseline-vs-gleaning benchmark runner
status: archived
priority: nice-to-have
created: 2026-03-21T15:56:03.1848729+01:00
updated: 2026-03-21T15:56:03.1848729+01:00
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

**Source:** #908 and docs/research/entity-extractor-gleaning-evaluation-plan.md §5

Build a reusable live benchmark runner in tests/benchmarks that compares the current single-pass extractor against the feature-flagged gleaning variant on the same curated gold corpus.

**Files:** tests/benchmarks/

**AC:**

1. Reuse the gold corpus and stable (normalized_name, entity_type) scorer from #906 for both variants.
2. Report micro recall plus per-type recall for baseline and gleaning in the same output.
3. Capture token totals, request counts, and estimated cost with a dedicated UsageTracker path for each variant.
4. Measure elapsed time with  ime.perf_counter() and summarize baseline vs gleaning runtime deltas.
5. Keep live execution opt-in via enchmark and pi markers or an equivalent explicit benchmark entry point.
