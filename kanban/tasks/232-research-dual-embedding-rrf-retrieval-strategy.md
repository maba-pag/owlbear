---
id: 232
title: 'Research: Dual embedding + RRF retrieval strategy'
status: archived
priority: needed
created: 2026-02-28T10:08:37.3820403+01:00
updated: 2026-02-28T23:54:13.0447284+01:00
started: 2026-02-28T13:52:38.0967373+01:00
completed: 2026-02-28T23:54:13.0447284+01:00
tags:
    - research
    - phase-9
    - knowledge-graph
    - memory
    - embedding
class: standard
---

Research dual-embedding with reciprocal rank fusion (RRF) for mixed-domain corpora (ISO norms, technical docs, general info).

Scope:
- pplx-embed-context-v1-0.6B for semantic + bge-m3 for lexical/sparse
- Two vec tables: vec_semantic, vec_lexical
- RRF to fuse results (1/(k+rank) formula)
- Local feasibility on Ryzen 8840U / 16GB RAM
- Honest model benchmarks (not marketing)

See copilot-instructions.md research checklist.
