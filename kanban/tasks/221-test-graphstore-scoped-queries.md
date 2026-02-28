---
id: 221
title: Test GraphStore scoped queries
status: archived
priority: important
created: 2026-02-28T01:17:31.6483871+01:00
updated: 2026-02-28T23:54:04.9501218+01:00
started: 2026-02-28T01:19:11.4813535+01:00
completed: 2026-02-28T23:54:04.9501218+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

TDD test task for #202. File: tests/test_knowledge_graph.py (extend existing).

AC:
- [ ] Test insert_entity(Entity(scope='project:owlbear')) persists scope to DB
- [ ] Test list_entities(scopes=['global','project:owlbear']) returns only matching entities
- [ ] Test list_entities(scopes=None) returns all entities (backwards compat)
- [ ] Test insert_edge(Edge(scope='agent:builder')) persists scope
- [ ] Test list_edges(scopes=['global']) filters by scope
- [ ] Test insert_document(Document(scope='project:foo')) persists scope
- [ ] Test list_documents(scopes=['global']) filters by scope
- [ ] Test get_entity/get_edge/get_document round-trips scope field
- [ ] Test delete_entity/delete_edge/delete_document works with scoped data

Depends on: #220 (test task), #197, #198
File: tests/test_knowledge_graph.py
