---
id: 274
title: Add graph community detection (Leiden algorithm)
status: archived
priority: important
created: 2026-02-28T14:21:36.1781468+01:00
updated: 2026-03-02T09:14:21.3555665+01:00
started: 2026-03-01T19:55:12.0944096+01:00
completed: 2026-03-02T09:14:21.3555665+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## Context
Apply GraphRAG's community detection pattern to our entity graph. Use python-igraph or leidenalg to detect communities and generate community summaries.
See docs/knowledge-pipeline-research.md S4.

## Acceptance Criteria
- [ ] Implement community detection on GraphStore entities
- [ ] Generate per-community summaries via PydanticAI agent
- [ ] Expose communities as retrieval context for RAG queries
