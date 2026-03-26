---
id: 15
title: Extract knowledge engine from v1
status: ideation
priority: needed
created: 2026-03-26T17:21:09.6126432+01:00
updated: 2026-03-26T17:21:09.6126432+01:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 7
class: standard
---

## Objective
Extract the knowledge base engine (graph + vector store + entity extraction) from v1 src/owlbear/ into v2 packages/knowledge/ as a standalone package.

## Acceptance Criteria
- [ ] packages/knowledge/src/owlbear_knowledge/ contains extracted modules
- [ ] SQLite graph store extracted and working
- [ ] Qdrant vector store integration extracted
- [ ] BGE-M3 embedding model support extracted
- [ ] Entity extraction pipeline extracted
- [ ] IntraDocGraphBuilder and InterDocGraphBuilder extracted
- [ ] Hybrid search (graph + vector) working
- [ ] Remove PydanticAI dependencies from knowledge code
- [ ] Remove daemon/hook dependencies from knowledge code
- [ ] Package has its own pyproject.toml with correct dependencies
- [ ] Unit tests pass for core operations (ingest, search, entity extraction)
- [ ] Package installable via uv pip install -e packages/knowledge/

## Context
Depends on F1 (monorepo skeleton). The knowledge engine is the most valuable v1 code. It needs surgical extraction - removing all PydanticAI, daemon, and hook dependencies while keeping the core graph/vector/embedding functionality intact.
