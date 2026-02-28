---
id: 258
title: 'Research: Graph-augmented retrieval implementation'
status: ideation
priority: needed
created: 2026-02-28T12:41:37.0366321+01:00
updated: 2026-02-28T14:54:41.0701588+01:00
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
Research #234 proposed graph-augmented retrieval: after vector search finds relevant chunks, traverse the entity graph to discover connected concepts. get_neighbors() expands results via edges. Depends on QdrantVectorStore (#249) for vector search and intra-document graph builder (#255) for denser graphs.

## Research Done
- docs/graph-augmented-retrieval-research.md — full analysis from #234
- Proposed: get_neighbors(), schema v4 (chunk_id on entities), GraphAugmentedRetriever

## Research Needed
- GraphAugmentedRetriever design: wraps QdrantVectorStore + GraphStore together?
- How many hops? 1-hop neighbors usually sufficient, 2-hop risks noise
- Re-ranking after expansion: how to score graph-expanded results vs vector results?
- Should entity embeddings also go into Qdrant? (entity description -> embed -> search)

## Acceptance Criteria
- [ ] Research doc updated or new doc in docs/
- [ ] Follow-up implementation tasks created
- [ ] GraphAugmentedRetriever API design proposed
- [ ] Quality assessment: graph expansion helps vs hurts on sample queries
