---
id: 202
title: GraphStore scoped queries — filter CRUD by scope
status: archived
priority: important
created: 2026-02-28T01:10:23.6192017+01:00
updated: 2026-02-28T23:53:49.7154015+01:00
started: 2026-02-28T01:11:43.7821004+01:00
completed: 2026-02-28T23:53:49.7154015+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
class: standard
---

Update GraphStore CRUD methods to write scope on insert and accept scopes filter on list/query.

File: src/owlbear/memory/knowledge/graph.py

AC:
- [ ] insert_entity(entity) writes entity.scope to the scope column
- [ ] insert_edge(edge) writes edge.scope to the scope column
- [ ] insert_document(doc) writes doc.scope to the scope column
- [ ] list_entities(entity_type=None, scopes=None) -> list[Entity]: when scopes is not None, adds WHERE scope IN (...) clause
- [ ] list_edges(source_id=None, target_id=None, scopes=None) -> list[Edge]: scopes filter
- [ ] list_documents(scopes=None) -> list[Document]: scopes filter
- [ ] get_entity/get_edge/get_document read scope column and populate model field
- [ ] scopes=None means no filter (all scopes, backwards compat)
- [ ] scopes=[] means no results (empty filter)
- [ ] Parameter type: scopes: list[str] | None = None

Depends on: #221 (test task), #197, #198
See docs/knowledge-scoping-research.md
