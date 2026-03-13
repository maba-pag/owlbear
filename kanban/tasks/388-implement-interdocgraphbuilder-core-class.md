---
id: 388
title: Implement InterDocGraphBuilder core class
status: archived
priority: important
created: 2026-03-01T20:15:51.2494184+01:00
updated: 2026-03-02T09:14:55.2710341+01:00
started: 2026-03-01T20:23:08.7255834+01:00
completed: 2026-03-02T09:14:55.2710341+01:00
tags:
    - phase-9
    - knowledge-graph
    - agent
class: standard
---

## Context
From #256 inter-document-graph-builder.md.
Follows IntraDocGraphBuilder pattern from graph_builder.py.

## Acceptance Criteria
- [ ] New file: src/owlbear/memory/knowledge/inter_doc_graph_builder.py
- [ ] Class InterDocGraphBuilder with PydanticAI Agent[None, ExtractionResult]
- [ ] Constructor: __init__(self, model: str | Model, vector_store: VectorStoreProtocol, graph_store: GraphStore)
- [ ] Constructor params top_k: int = 10, cosine_threshold: float = 0.70
- [ ] System prompt adapted for cross-document relationship inference (entities from different documents)
- [ ] Method: async def build(self, entities: list[Entity], scope: str = 'global', document_id: str | None = None) -> GraphBuildResult
- [ ] Pre-filter: for each entity, get embedding via vector_store.get_embedding(entity.id), then search_similar(embedding, top_k=top_k, embedding_type='entity', scopes=[scope])
- [ ] Cross-doc filter: exclude matched entities where graph_store.get_entity(matched_id).document_id == source entity.document_id
- [ ] Deduplication: skip entity pairs that already have inter-doc edges (check via graph_store.list_edges or metadata source)
- [ ] Cosine threshold: discard pairs with score < self.cosine_threshold
- [ ] Batch pairs into groups of ~40 for LLM inference (one agent.run() call per batch)
- [ ] LLM prompt includes both entities names, descriptions, and entity_types
- [ ] Edge stamping: weight=0.4, metadata={'source': 'inter_doc_inference', 'doc_pair': [doc_a_id, doc_b_id]}, scope=scope
- [ ] Error handling: failed agent.run() calls skip the batch with logger.warning (matching IntraDocGraphBuilder pattern)
- [ ] Return GraphBuildResult(edges_added=len(edges), edges=edges)
- [ ] Add InterDocGraphBuilder and re-export from __init__.py __all__

## Dependencies
Depends on #389 (tests written first, TDD).
