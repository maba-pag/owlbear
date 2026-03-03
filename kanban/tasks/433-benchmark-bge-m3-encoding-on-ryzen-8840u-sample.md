---
id: 433
title: Benchmark bge-m3 encoding on Ryzen 8840U sample corpus
status: ideation
priority: important
created: 2026-03-03T16:18:56.9973416+01:00
updated: 2026-03-03T16:18:56.9973416+01:00
tags:
    - phase-10
    - test
    - embedding
class: standard
---

Measure actual RAM and latency for BgeM3EmbeddingProvider on Ryzen 8840U. Test batch sizes 4/8/16/32. Record peak RSS, chunks/sec for dense-only vs all-three outputs. See docs/bge-m3-evaluation.md. AC: Benchmark script in tests/benchmarks/, actual numbers documented.
