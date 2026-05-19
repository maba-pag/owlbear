---
id: 913
title: Test EntityExtractor recall harness and reporting (RED)
status: archived
priority: nice-to-have
created: 2026-03-21T15:52:58.6702439+01:00
updated: 2026-03-21T15:52:58.6702439+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - test
    - type:test
    - phase-research
parent: 906
depends_on:
    - 912
class: standard
---

**Source:** #906 and docs/research/entity-extractor-code-corpus-recall-harness.md
**Depends on:** #912

TDD RED phase for the recall scorer, runner, and reporting layer.

**AC:**

1. Add focused tests under tests/benchmarks/ for a repo-native EntityExtractor recall harness rather than reusing ranx retrieval helpers.
2. The scorer contract reports micro recall and per-type recall from predicted versus gold entity keys, and includes predicted entity count in the formatted output or summary rows.
3. The runner tests use stubbed extractor outputs and require no real model calls in normal test runs; any live benchmark entry point remains opt-in.
4. The harness or formatted report includes run instructions or output text that links back to docs/research/entity-extractor-code-corpus-recall-harness.md.
5. The new tests fail on current HEAD before the harness and reporting code is implemented.

**Likely files:** tests/benchmarks/test_entity_extractor_recall.py and tests/benchmarks/bench_entity_extractor_recall.py.
