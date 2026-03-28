---
id: 34
title: Knowledge package integration + hybrid search
status: ideation
priority: needed
created: 2026-03-26T18:33:53.2231299+01:00
updated: 2026-03-26T18:33:53.2231299+01:00
tags:
    - phase-1
    - scope:knowledge
    - type:test
depends_on:
    - 33
class: standard
---

## Objective

Assemble the complete knowledge package: wire up hybrid search (graph + vector), run integration tests, verify package installability.

## Acceptance Criteria

- [ ] Extract query_service.py (hybrid search: graph + vector fusion)
- [ ] Extract retrieval.py (result ranking and formatting)
- [ ] Extract chunker.py (document chunking for embeddings)
- [ ] Hybrid search works: query returns results from both graph and vector stores
- [ ] Full ingest-to-search cycle test: ingest document, extract entities, build graph, embed chunks, search by query
- [ ] Package installable: `uv pip install -e packages/knowledge/` succeeds
- [ ] All cross-module imports work within the package
- [ ] README.md in packages/knowledge/ with setup instructions (Qdrant, BGE-M3 model download)

## Context

Depends on #33 (entity extraction). Subtask 4/4 of knowledge engine extraction. After this, mcp-knowledge (#16) can be built on top of the complete package.
