---
id: 32
title: Extract vector store + embedding pipeline
status: ideation
priority: needed
created: 2026-03-26T18:33:43.753881+01:00
updated: 2026-03-26T18:33:43.753881+01:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 15
class: standard
---

## Objective

Extract the vector store (Qdrant) and embedding pipeline (BGE-M3) from v1 into packages/knowledge/.

## Acceptance Criteria

- [ ] Extract qdrant.py (Qdrant client wrapper, collection management)
- [ ] Extract embeddings.py (BGE-M3 embedding model loading + encode)
- [ ] Remove PydanticAI/daemon imports from extracted modules
- [ ] Qdrant strategy: local file-based mode (no Docker) using qdrant-client with local persistence
- [ ] BGE-M3 model: document download/cache location in package README or config
- [ ] Add qdrant-client and sentence-transformers to package dependencies
- [ ] Unit tests: embedding generation, vector store insert/search
- [ ] Integration with graph store from #15 (shared models/schema)

## Context

Depends on #15 (graph store foundation). Subtask 2/4 of knowledge engine extraction. v1 modules: qdrant.py, embeddings.py.
