---
id: 375
title: Evaluate bge-m3 via FlagEmbedding (deferred to post-Qdrant)
status: archived
priority: nice-to-have
created: 2026-03-01T20:13:51.6264167+01:00
updated: 2026-03-03T16:40:10.7167974+01:00
started: 2026-03-01T20:22:46.345354+01:00
completed: 2026-03-03T16:40:10.7167974+01:00
tags:
    - phase-10
    - embedding
    - research
class: standard
---

From #258 graph-augmented-retrieval-research.md. When/if Qdrant migration (#236) happens, evaluate bge-m3 as single-model replacement for bge-small + SPLADE++. Benchmark memory/latency on Ryzen 8840U. AC: Decision doc comparing bge-m3 vs dual-FastEmbed on quality, latency, and resource usage. Depends on #258.
