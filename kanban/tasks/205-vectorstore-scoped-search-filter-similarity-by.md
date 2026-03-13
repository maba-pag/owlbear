---
id: 205
title: VectorStore scoped search — filter similarity by scope
status: archived
priority: important
created: 2026-02-28T01:10:29.3966202+01:00
updated: 2026-02-28T23:53:51.9884162+01:00
started: 2026-02-28T01:11:44.2641321+01:00
completed: 2026-02-28T23:53:51.9884162+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
class: standard
---

Update VectorStore to write scope on store and post-filter by scope on search.

File: src/owlbear/memory/knowledge/vectors.py

AC:
- [ ] store_embedding(entity_or_doc_id, embedding, embedding_type, scope='global') writes scope to embedding_rowid_map
- [ ] search_similar(..., scopes: list[str] | None = None): when scopes is not None, over-fetch k*3 from vec0, then post-filter via embedding_rowid_map WHERE scope IN (...)
- [ ] Post-filter happens after bridge-table rowid resolution (same point as existing reranker pattern)
- [ ] _search_with_reranker also respects scopes parameter
- [ ] scopes=None means no filter (backwards compat)
- [ ] get_embedding unchanged (no scope filter needed for single-ID lookup)
- [ ] delete_embedding unchanged (deletes by ID regardless of scope)

Depends on: #222 (test task), #197
See docs/research/knowledge-scoping.md
