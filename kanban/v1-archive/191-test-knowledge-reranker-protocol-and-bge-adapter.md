---
id: 191
title: Test knowledge reranker — protocol and BGE adapter
status: archived
priority: important
created: 2026-02-27T22:18:07.3083066+01:00
updated: 2026-02-28T23:53:40.7335267+01:00
started: 2026-02-27T23:47:21.4804646+01:00
completed: 2026-02-28T23:53:40.7335267+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

Write tests in tests/test_knowledge_reranker.py for src/owlbear/memory/knowledge/reranker.py. Test: (1) RerankerProvider is a runtime_checkable Protocol with rerank(query, passages) -> list[tuple[int, float]] (2) BGERerankerProvider satisfies the RerankerProvider protocol (3) BGERerankerProvider lazily loads model on first rerank() call (mock FlagReranker) (4) rerank() returns (index, score) pairs sorted by score descending (5) VectorStore.search_similar accepts optional reranker parameter (6) With reranker: retrieves top_k*3 candidates, reranks, returns top_k (7) Without reranker: behavior unchanged (backward compatible) (8) Empty passages returns empty list
