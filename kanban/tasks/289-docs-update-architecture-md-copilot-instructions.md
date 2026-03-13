---
id: 289
title: 'Docs: update architecture.md, copilot-instructions.md, README.md for phase-9 knowledge pipeline'
status: archived
priority: critical
created: 2026-03-01T01:15:40.3390597+01:00
updated: 2026-03-01T17:08:11.2808077+01:00
started: 2026-03-01T01:56:30.5603557+01:00
completed: 2026-03-01T17:08:11.2808077+01:00
tags:
    - docs
    - phase-9
    - knowledge-graph
depends_on:
    - 288
class: standard
---

## Scope
Docs-only task: update 3 documentation files with 9 corrections identified by the phase-9 docs audit.
See [docs/research/docs-audit-phase9.md](docs/research/docs-audit-phase9.md) for full analysis.

## Acceptance Criteria

### architecture.md (7 corrections)
- [ ] Update knowledge package listing: add graph_builder.py, protocol.py, reranker.py; replace vectors.py with qdrant.py
- [ ] Update file count from 11 to 14 (13 modules + __init__.py)
- [ ] Update schema.py description: 'SQLite DDL, migrations (v1-v4)' -- remove sqlite-vec reference
- [ ] Update embeddings.py description: 'EmbeddingProvider protocol + BgeM3EmbeddingProvider (idle-timeout)' -- replace FastEmbedProvider
- [ ] Update Section 4.6 memory system status: migration to Qdrant+BGE-M3 is DONE, remove 'planned' language
- [ ] Update Section 7 phase 9 status: change from Active to Done
- [ ] Update Section 8 design decisions: 'SQLite (schema) + Qdrant (vectors) + BGE-M3 (embeddings)' -- replace sqlite-vec

### copilot-instructions.md (1 correction)
- [ ] Update tech stack table Knowledge row: replace 'Knowledge (planned) | Knowledge graph + vector DB | DB tech TBD' with 'Knowledge | SQLite (graph) + Qdrant (vectors) + BGE-M3 | Knowledge graph with hybrid vector search; schema v4; idle-timeout model unloading'

### README.md (1 correction)
- [ ] Update architecture bullet: replace 'Knowledge graph + vector DB (planned)' with 'SQLite knowledge graph + Qdrant hybrid vector search (BGE-M3)'

## Out of scope
- knowledge/__init__.py exports -> separate builder task #290
- Docstrings: verified complete by researcher
- sources.md: verified complete by researcher
