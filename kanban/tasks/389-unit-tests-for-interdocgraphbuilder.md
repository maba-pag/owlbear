---
id: 389
title: Unit tests for InterDocGraphBuilder
status: archived
priority: important
created: 2026-03-01T20:16:01.2169957+01:00
updated: 2026-03-02T09:14:57.1290711+01:00
started: 2026-03-01T20:23:09.9153262+01:00
completed: 2026-03-02T09:14:57.1290711+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

## Context
TDD tests for InterDocGraphBuilder. Write before implementation.
See docs/research/inter-document-graph-builder.md for design.
Follows test pattern from tests/test_graph_builder.py (IntraDocGraphBuilder tests).

## Acceptance Criteria
- [ ] File: tests/test_inter_doc_graph_builder.py
- [ ] Mock VectorStoreProtocol (search_similar returns controlled (entity_id, score) tuples; get_embedding returns controlled dense vectors)
- [ ] Mock GraphStore (get_entity returns controlled Entity objects with document_id set)
- [ ] Mock PydanticAI Agent (agent.run returns controlled ExtractionResult with edges)
- [ ] Test: build() with < 2 entities returns empty GraphBuildResult (edges_added=0)
- [ ] Test: embedding pre-filter calls vector_store.search_similar() per entity with embedding_type='entity' and scopes=[scope]
- [ ] Test: pre-filter results exclude same-document entities (only cross-doc entity pairs kept)
- [ ] Test: cosine threshold filtering — pairs with score below 0.70 (default) excluded
- [ ] Test: configurable cosine_threshold — pass 0.50, verify weaker matches included
- [ ] Test: configurable top_k — pass top_k=5, verify search_similar called with top_k=5
- [ ] Test: batch grouping — entity pairs grouped into batches of ~40 per LLM call
- [ ] Test: edge stamping — all edges have weight=0.4, metadata contains 'source': 'inter_doc_inference' and 'doc_pair': [doc_a_id, doc_b_id], correct scope
- [ ] Test: build() returns GraphBuildResult with correct edges_added count and edges list
- [ ] Test: error handling — failed agent.run() on one batch logs warning and skips it; other batches still produce edges
- [ ] Test: deduplication — entity pairs that already have inter-doc edges (checked via graph_store) are skipped
- [ ] >= 90%% coverage of inter_doc_graph_builder module
