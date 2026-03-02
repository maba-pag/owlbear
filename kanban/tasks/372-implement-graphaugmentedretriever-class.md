---
id: 372
title: Implement GraphAugmentedRetriever class
status: archived
priority: needed
created: 2026-03-01T20:13:26.5426654+01:00
updated: 2026-03-02T09:16:52.3434747+01:00
started: 2026-03-01T20:22:42.1443839+01:00
completed: 2026-03-02T09:16:52.3434747+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 422
class: standard
---

From #258 graph-augmented-retrieval-research.md. New class at src/owlbear/memory/knowledge/retrieval.py (~100 LOC). AC: - Class: GraphAugmentedRetriever.__init__(self, vector_store, graph_store, embedding_provider, *, expansion_depth: int = 1, max_expansion_tokens: int = 2000, max_neighbors_per_entity: int = 10, expansion_enabled: bool = True) - Method: retrieve(self, query: str, top_k: int = 5, scopes: list[str] | None = None) -> RetrievalResult - Pipeline: embed query -> vector search_similar -> resolve chunk_ids to entity IDs (via entities.chunk_id) -> get_neighbors per entity -> format neighbor descriptions -> budget-cap expansion text - RetrievalResult model: chunks: list[tuple[str,float]], expansion_text: str, entities_found: int - expansion_depth=0 returns only vector search results (no graph traversal) - expansion_enabled=False skips graph expansion entirely (kill switch) - Token budget: expansion_text never exceeds max_expansion_tokens words (len(text.split()) heuristic) - max_neighbors_per_entity limits fan-out per seed entity - Export from owlbear.memory.knowledge.__init__ - Depends on #370, #371, test task #422
