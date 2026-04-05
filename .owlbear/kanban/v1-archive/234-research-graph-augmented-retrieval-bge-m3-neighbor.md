---
id: 234
title: 'Research: Graph-augmented retrieval (bge-m3 + neighbor expansion)'
status: archived
priority: needed
created: 2026-02-28T10:08:56.6947307+01:00
updated: 2026-02-28T23:54:15.453947+01:00
started: 2026-02-28T13:52:39.4996864+01:00
completed: 2026-02-28T23:54:15.453947+01:00
tags:
    - research
    - phase-9
    - knowledge-graph
    - memory
    - embedding
class: standard
---

Research graph-augmented generation retrieval for knowledge pipeline.

Scope:
- bge-m3 for embedding (dense + sparse in one model)
- On search: join neighboring graph nodes for context expansion
- How to combine vector similarity with graph traversal
- Works with current GraphStore/VectorStore architecture?
- Local feasibility on Ryzen 8840U / 16GB RAM
- Compare enriched context vs plain vector search

See copilot-instructions.md research checklist.
