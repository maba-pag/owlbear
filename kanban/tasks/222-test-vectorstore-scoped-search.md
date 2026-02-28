---
id: 222
title: Test VectorStore scoped search
status: archived
priority: important
created: 2026-02-28T01:17:41.1807005+01:00
updated: 2026-02-28T23:54:05.7787291+01:00
started: 2026-02-28T01:19:11.992087+01:00
completed: 2026-02-28T23:54:05.7787291+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

TDD test task for #205. File: tests/test_knowledge_vectors.py (extend existing).

AC:
- [ ] Test store_embedding() with scope writes scope to embedding_rowid_map
- [ ] Test search_similar(scopes=['global']) returns only global-scoped results
- [ ] Test search_similar(scopes=['global','project:x']) returns union of matching scopes
- [ ] Test search_similar(scopes=None) returns all results (backwards compat)
- [ ] Test over-fetch and post-filter: insert 10 entries across 3 scopes, search with 1 scope, verify only matching scope returned
- [ ] Test scoped search works with reranker path (_search_with_reranker)

Depends on: #197
File: tests/test_knowledge_vectors.py
