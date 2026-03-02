---
id: 252
title: Benchmark hybrid search quality
status: archived
priority: important
created: 2026-02-28T12:39:52.6609423+01:00
updated: 2026-03-02T05:41:58.9910943+01:00
started: 2026-03-01T18:56:06.0454716+01:00
completed: 2026-03-02T05:41:58.9910943+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
    - test
depends_on:
    - 250
class: standard
---

## Context
Verify the Qdrant+bge-m3 hybrid search actually outperforms the old bge-small dense-only search. Measure nDCG@10 + keyword precision on sample queries.

## Research Needed
- What test corpus to use? OwlBear's own docs? Sample ISO clauses?
- How to measure nDCG@10 without ground truth labels — manual labeling?
- What's the baseline? bge-small dense (current) vs bge-m3 hybrid (new)

## Acceptance Criteria
- [ ] Benchmark script in tests/benchmarks/
- [ ] Sample corpus: 50+ chunks from mixed domains (technical + regulatory + general)
- [ ] Query set: 20+ queries covering different retrieval needs
- [ ] nDCG@10 comparison: dense-only vs sparse-only vs hybrid vs hybrid+ColBERT
- [ ] Latency measurement: end-to-end search time
- [ ] Results documented in task body or linked doc
- [ ] TDD where applicable
