---
id: 373
title: Integrate graph expansion into search_similar flow
status: archived
priority: important
created: 2026-03-01T20:13:34.4810537+01:00
updated: 2026-03-02T09:16:54.667887+01:00
started: 2026-03-01T20:22:43.478257+01:00
completed: 2026-03-02T09:16:54.667887+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 427
    - 258
    - 372
class: standard
---

Integrate GraphAugmentedRetriever into KnowledgeQueryService so knowledge queries can opt into graph expansion. Composition approach (not VectorStore protocol modification).

See docs/research/graph-augmented-retrieval.md for design rationale. Depends on #258 (research), #372 (GraphAugmentedRetriever impl), #427 (TDD test task).

## AC — KnowledgeQueryService changes

- [ ] KnowledgeQueryService.__init__ accepts optional retriever: GraphAugmentedRetriever | None = None
- [ ] When retriever is not None, _query() delegates embed+search to retriever.retrieve(query, top_k, scopes) instead of calling _embed() and vector_store.search_similar() directly
- [ ] _query() still resolves doc IDs via graph_store.get_document() using the chunks from RetrievalResult — document resolution stays in the service
- [ ] Threshold filtering (>= similarity_threshold) still applied to chunks from RetrievalResult
- [ ] expansion_text from RetrievalResult appended to output after doc snippets, under a 'Related concepts:' header
- [ ] Total word count (doc snippets + expansion text) respects max_tokens budget — expansion_text is trimmed if the budget is exhausted by doc snippets
- [ ] When expansion_text is empty string, no 'Related concepts:' section appears in output
- [ ] When retriever is None (default), behavior is identical to current implementation — backward compatible

## AC — Config + Bootstrap wiring

- [ ] OwlBearSettings gains knowledge_graph_expansion: bool = True (default: enabled when knowledge subsystem is available)
- [ ] _build_knowledge_toolset() creates GraphAugmentedRetriever(vector_store, graph_store, embedding_provider) when knowledge_graph_expansion=True
- [ ] _build_knowledge_toolset() passes the retriever to KnowledgeQueryService constructor
- [ ] When knowledge_graph_expansion=False, no retriever created, service behaves as before

## AC — Interface invariants

- [ ] VectorStoreProtocol.search_similar() signature is NOT modified (no graph_expand param)
- [ ] No schema changes required (still schema v5)
- [ ] GraphAugmentedRetriever class is not modified — only consumed
- [ ] Export: no new public API beyond the config field

## Patterns to follow

- KnowledgeQueryService._embed() pattern for embed_hybrid fallback — retriever handles this internally, so service skips _embed() when retriever is used
- Bootstrap _build_knowledge_toolset() pattern — add retriever construction adjacent to service construction
- OwlBearSettings field_validator pattern for bool fields (none needed, bool is simple)
