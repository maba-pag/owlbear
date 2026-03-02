---
id: 427
title: Unit tests for KnowledgeQueryService graph expansion integration
status: archived
priority: important
created: 2026-03-02T01:17:09.4173998+01:00
updated: 2026-03-02T09:15:24.8919221+01:00
started: 2026-03-02T01:44:54.0905579+01:00
completed: 2026-03-02T09:15:24.8919221+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD tests for #373. Tests for KnowledgeQueryService when constructed with a GraphAugmentedRetriever.

AC:
- [ ] test file: tests/test_knowledge_query_service_expansion.py (or extend tests/test_knowledge_query_service.py)
- [ ] Test: when retriever=None (default), query_for_context() behaves identically to current — vector search + doc resolution, no expansion text
- [ ] Test: when retriever is provided, _query() delegates embed+search to retriever.retrieve() instead of doing its own vector search
- [ ] Test: expansion_text from RetrievalResult appended to output after doc snippets under a 'Related concepts:' section
- [ ] Test: total word count of doc snippets + expansion text respects max_tokens budget
- [ ] Test: threshold filtering still applied to chunks returned by retriever
- [ ] Test: scopes forwarded to retriever.retrieve(scopes=...) when set
- [ ] Test: when retriever returns empty chunks, returns None (same as current no-results)
- [ ] Test: when retriever returns chunks but expansion_text is empty, output has no 'Related concepts' section
- [ ] Test: exception in retriever.retrieve() caught by outer try/except, returns None with WARNING log
- [ ] Test: bootstrap creates GraphAugmentedRetriever and passes to KnowledgeQueryService when knowledge_graph_expansion=True
- [ ] Test: bootstrap does NOT create retriever when knowledge_graph_expansion=False
- [ ] All tests use mocks (no real embedding model or Qdrant)
- [ ] >= 90%% coverage of changed lines

Depends on: none (test-first)
