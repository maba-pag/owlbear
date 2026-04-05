---
id: 117
title: Test knowledge graph CRUD operations
status: archived
priority: high
created: 2026-02-27T03:42:40.80036+01:00
updated: 2026-02-27T13:21:47.6279228+01:00
started: 2026-02-27T12:47:47.4409198+01:00
completed: 2026-02-27T13:21:47.6279228+01:00
tags:
    - memory
    - knowledge-graph
    - test
    - phase-2
depends_on:
    - 107
class: standard
---

TDD test suite for `owlbear.memory.knowledge.graph`. Write tests BEFORE implementation (#109).

## Acceptance Criteria

- [ ] New file: `tests/test_knowledge_graph.py`
- [ ] Shared fixture: `db_conn` — in-memory SQLite connection with `init_db` applied
- [ ] Shared fixture: `graph_store` — `GraphStore(db_conn)`
- [ ] Test `insert_entity` + `get_entity` round-trip (construct Entity, insert, get by id, compare)
- [ ] Test `get_entity` returns `None` for nonexistent id
- [ ] Test `insert_entity` with duplicate id raises appropriate error
- [ ] Test `list_entities` returns all, `list_entities(entity_type=...)` filters correctly
- [ ] Test `delete_entity` returns `True` and removes entity, cascades edges
- [ ] Test `delete_entity` returns `False` for nonexistent id
- [ ] Test `insert_edge` + `get_edge` round-trip
- [ ] Test `insert_edge` raises when source/target entity doesn't exist
- [ ] Test `list_edges` with source_id and target_id filters
- [ ] Test `delete_edge` returns `True`/`False` correctly
- [ ] Test `insert_document` + `get_document` round-trip
- [ ] Test `list_documents` returns all documents
- [ ] Test metadata round-trip (dict stored as JSON, deserialized on read)
- [ ] All tests initially fail (import error) until #109 implements the module
- [ ] `ruff check` clean on test file
