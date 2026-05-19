---
id: 914
title: Build EntityExtractor recall harness and reporting
status: archived
priority: nice-to-have
created: 2026-03-21T15:53:06.4344313+01:00
updated: 2026-03-21T15:53:06.4344313+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - type:build
    - phase-research
parent: 906
depends_on:
    - 912
    - 913
class: standard
---

**Source:** #906 and docs/research/entity-extractor-code-corpus-recall-harness.md
**Depends on:** #912 and #913

Build the EntityExtractor recall harness and reporting on top of the checked-in corpus.

**AC:**

1. Add a repo-native benchmark harness under tests/benchmarks/ that loads the checked-in corpus, runs the current EntityExtractor interface, and scores predicted entities against gold keys with a custom scorer.
2. The harness reports micro recall, per-type recall, and predicted entity count without adding sklearn or spaCy as runtime dependencies.
3. Normal tests use stubbed extractor behavior and make no real model call; any live benchmark entry point remains opt-in and marked with @pytest.mark.benchmark.
4. The formatted output or run instructions link back to docs/research/entity-extractor-code-corpus-recall-harness.md.
5. The RED tests from #913 and the corpus task #912 pass.

**Likely files:** tests/benchmarks/bench_entity_extractor_recall.py and supporting helpers under tests/benchmarks/.
