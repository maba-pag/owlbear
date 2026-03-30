---
id: 160
title: Upgrade query_service.py with retriever delegation and hybrid search
status: ideation
priority: needed
created: 2026-03-29T19:37:32.4203226+02:00
updated: 2026-03-29T19:37:32.4203226+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 159
class: standard
---

## Objective
Upgrade v2 query_service.py to match v1 capabilities: add query_for_context() text formatting, wire GraphAugmentedRetriever delegation, add Qdrant hybrid search (dense+sparse prefetch+RRF).

## Acceptance Criteria
- [ ] query_for_context(prompt, max_tokens, top_k) returns formatted text within token budget or None
- [ ] KnowledgeQueryService accepts optional retriever parameter, delegates _search_chunks() when set
- [ ] QdrantVectorStore gains hybrid search via prefetch (dense + sparse) with RRF fusion
- [ ] Hybrid search returns results from both dense and sparse indexes
- [ ] Fallback to dense-only search when no sparse vectors present
- [ ] Unit tests for retriever delegation path and direct search path

## Context
Split from #34 per docs/research/knowledge-package-integration-hybrid-search.md. Depends on #159 (retrieval.py extraction). v1 query_service.py (250 LOC) has proven architecture.
