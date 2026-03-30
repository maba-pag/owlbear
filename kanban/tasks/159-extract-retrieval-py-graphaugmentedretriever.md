---
id: 159
title: Extract retrieval.py (GraphAugmentedRetriever)
status: backlog
priority: needed
created: 2026-03-29T19:37:22.7410344+02:00
updated: 2026-03-30T08:29:53.7433391+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 32
class: standard
---

## Objective
Extract v1/src/owlbear/memory/knowledge/retrieval.py (228 LOC) into packages/knowledge/src/owlbear_knowledge/retrieval.py.

## Acceptance Criteria
- [ ] retrieval.py exists with GraphAugmentedRetriever class and RetrievalResult model
- [ ] Import paths migrated: owlbear.memory.knowledge.* to owlbear_knowledge.*
- [ ] GraphAugmentedRetriever.retrieve() implements: embed query, vector search, seed resolution, BFS expansion, budget cap
- [ ] RetrievalResult(chunks, expansion_text, entities_found) is a frozen Pydantic BaseModel
- [ ] Zero PydanticAI or daemon imports
- [ ] Unit tests with mock vector store, graph store, and embedding provider

## Context
Split from #34 per docs/research/knowledge-package-integration-hybrid-search.md. v1 retrieval.py has proven design (dual-path search + BFS expansion + token budget). Subtask of knowledge package integration.
