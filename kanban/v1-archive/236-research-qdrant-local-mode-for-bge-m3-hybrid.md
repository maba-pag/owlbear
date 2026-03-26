---
id: 236
title: 'Research: Qdrant local mode for bge-m3 hybrid search (dense+sparse+ColBERT)'
status: archived
priority: needed
created: 2026-02-28T10:09:17.6534065+01:00
updated: 2026-02-28T23:54:16.8767052+01:00
started: 2026-02-28T13:57:01.0328189+01:00
completed: 2026-02-28T23:54:16.8767052+01:00
tags:
    - research
    - phase-9
    - knowledge-graph
    - memory
    - embedding
class: standard
---

Research Qdrant in local/embedded mode as vector DB replacement for sqlite-vec.

Scope:
- Qdrant local mode (no Docker, embedded in Python process)
- bge-m3 native hybrid: dense + sparse + ColBERT vectors in a single query
- Named vectors for multi-representation storage
- Compare: Qdrant local vs current sqlite-vec architecture
- Migration path from sqlite-vec to Qdrant
- Resource usage: RAM, disk, query latency on Ryzen 8840U/16GB
- qdrant-client Python SDK — API surface for hybrid search
- Prefetch + fusion query patterns

See copilot-instructions.md research checklist.
