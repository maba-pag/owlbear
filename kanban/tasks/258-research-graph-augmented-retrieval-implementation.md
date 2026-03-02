---
id: 258
title: 'Research: Graph-augmented retrieval implementation'
status: archived
priority: needed
created: 2026-02-28T12:41:37.0366321+01:00
updated: 2026-03-02T09:14:16.7865642+01:00
started: 2026-03-01T18:48:23.8032403+01:00
completed: 2026-03-02T09:14:16.7865642+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
depends_on:
    - 249
    - 255
class: standard
---

## Context
Research #234 proposed graph-augmented retrieval: after vector search finds relevant chunks, traverse the entity graph to discover connected concepts. get_neighbors() expands results via edges.
Depends on QdrantVectorStore (#249) and intra-document graph builder (#255).

## Research Done
- docs/graph-augmented-retrieval-research.md -- full analysis (271 lines)
- Proposed: get_neighbors(), schema v5 (chunk_id on entities), GraphAugmentedRetriever

## Acceptance Criteria
- [x] Research doc updated or new doc in docs/ -- docs/graph-augmented-retrieval-research.md (271 lines)
- [x] Follow-up implementation tasks created -- #370-373 (all done)
- [x] GraphAugmentedRetriever API design proposed -- retrieve(query, top_k, scopes) -> RetrievalResult
- [x] Quality assessment -- graph expansion helps for cross-reference/policy-lookup failure modes; 1-hop sufficient, 2-hop adds noise
