---
id: 233
title: 'Research: Retrieve-and-rerank strategy (pplx-embed + bge-reranker)'
status: archived
priority: needed
created: 2026-02-28T10:08:45.7846176+01:00
updated: 2026-02-28T23:54:14.8243646+01:00
started: 2026-02-28T13:52:38.6428014+01:00
completed: 2026-02-28T23:54:14.8243646+01:00
tags:
    - research
    - phase-9
    - knowledge-graph
    - memory
    - embedding
class: standard
---

Research retrieve-and-rerank pipeline for mixed-domain knowledge.

Scope:
- pplx-embed-context-v1-0.6B for embedding
- bge-reranker-v2-m3 for reranking search results
- Compare with current BGE-small + FlagReranker baseline
- Local feasibility (0.6B models, Ryzen 8840U / 16GB RAM)
- Honest benchmark comparison (ignore marketing, check MTEB/BEIR)
- Latency: embed time, rerank time for typical queries

See copilot-instructions.md research checklist.
