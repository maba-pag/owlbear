---
id: 434
title: Evaluate ColBERT scalar quantization in Qdrant
status: backlog
priority: nice-to-have
created: 2026-03-03T16:19:03.780587+01:00
updated: 2026-03-04T07:24:24.1708506+01:00
started: 2026-03-04T07:24:24.1708506+01:00
tags:
    - phase-10
    - knowledge-graph
    - embedding
blocked: true
block_reason: Needs 1 more source on multivector quantization quality impact + eval methodology. Defer until corpus exceeds 5K chunks.
class: standard
---

Test uint8 quantization on ColBERT multivectors in Qdrant. Measure storage reduction and quality impact on sample queries. See docs/bge-m3-evaluation.md.

## AC

- [ ] uint8 scalar quantization config tested on ColBERT multivectors
- [ ] Storage reduction delta measured and documented
- [ ] Quality impact delta measured on sample queries and documented
