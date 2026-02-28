---
id: 235
title: 'Research: Embedding model shootout — local feasibility and honest benchmarks'
status: archived
priority: needed
created: 2026-02-28T10:09:07.4049223+01:00
updated: 2026-02-28T23:54:16.0971857+01:00
started: 2026-02-28T13:57:00.5160163+01:00
completed: 2026-02-28T23:54:16.0971857+01:00
tags:
    - research
    - phase-9
    - knowledge-graph
    - memory
    - embedding
class: standard
---

Honest, marketing-free comparison of embedding models for mixed-domain knowledge (ISO norms 35%%, technical docs 50%%, general info 15%%).

Scope:
- Models: bge-small-en-v1.5 (current), bge-m3, pplx-embed-context-v1-0.6B, pplx-embed-context-v1-4B, nomic-embed-text-v1.5, e5-mistral-7b-instruct
- Benchmarks: MTEB, BEIR retrieval, domain-specific (legal, technical)
- Local resource usage: RAM, VRAM, inference speed on Ryzen 8840U/16GB
- Can two 0.6B models run in parallel? vs one 4B model?
- Multilingual support (relevant for EU norms/laws)
- Dense vs sparse vs hybrid capabilities per model
- WARNING: marketing comparisons are misleading, use only third-party benchmarks

See copilot-instructions.md research checklist.
