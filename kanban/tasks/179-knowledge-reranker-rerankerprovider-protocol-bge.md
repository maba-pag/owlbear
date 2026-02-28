---
id: 179
title: Knowledge reranker — RerankerProvider protocol + bge-reranker adapter
status: archived
priority: important
created: 2026-02-27T22:10:30.7927249+01:00
updated: 2026-02-28T23:53:27.6229962+01:00
started: 2026-02-27T22:12:08.5713251+01:00
completed: 2026-02-28T23:53:27.6229962+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 191
class: standard
---

Module: src/owlbear/memory/knowledge/reranker.py | Test: tests/test_knowledge_reranker.py | See docs/knowledge-ingestion-research.md S3.3.

AC:
- RerankerProvider runtime_checkable Protocol: rerank(query: str, passages: list[str]) -> list[tuple[int, float]] (index, score pairs sorted by descending score)
- BGERerankerProvider class satisfying RerankerProvider protocol
- Lazy model loading on first rerank() call (same pattern as FastEmbedProvider in embeddings.py)
- Uses FlagEmbedding.FlagReranker (optional dependency — import guarded)
- VectorStore.search_similar() gains optional reranker: RerankerProvider | None = None parameter
- With reranker: retrieves top_k * 3 candidates from vec0, reranks, returns top_k
- Without reranker: behavior unchanged (backward compatible — existing tests still pass)
- Empty passages input returns empty list
- Independent of ingest pipeline — query-time enhancement only
- ruff clean, all tests in tests/test_knowledge_reranker.py pass
