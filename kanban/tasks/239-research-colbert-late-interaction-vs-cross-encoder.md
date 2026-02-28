---
id: 239
title: 'Research: ColBERT late-interaction vs cross-encoder reranking tradeoff'
status: archived
priority: needed
created: 2026-02-28T11:10:50.1389358+01:00
updated: 2026-02-28T23:54:18.9391063+01:00
started: 2026-02-28T13:52:08.5173685+01:00
completed: 2026-02-28T23:54:18.9391063+01:00
tags:
    - research
    - phase-9
    - knowledge-graph
    - embedding
class: standard
---

bge-m3 ColBERT vectors enable Qdrant multivector max_sim reranking. Compare quality vs current bge-reranker-v2-m3 (FlagReranker). If ColBERT suffices, we can drop the cross-encoder path entirely. AC: Quality comparison with sources, latency estimates, recommendation.
