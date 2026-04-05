---
id: 220
title: Test schema v3 migration and model scope fields
status: archived
priority: important
created: 2026-02-28T01:17:21.6365146+01:00
updated: 2026-02-28T23:54:04.1250326+01:00
started: 2026-02-28T01:19:10.9574341+01:00
completed: 2026-02-28T23:54:04.1250326+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

TDD test task for #197 and #198. File: tests/test_knowledge_schema.py (extend existing) + tests/test_knowledge_models.py (extend existing).

AC:
- [ ] Test _migrate_v2_to_v3() adds scope TEXT DEFAULT 'global' to entities, documents, edges, chunks, embedding_rowid_map
- [ ] Test _migrate_v2_to_v3() is idempotent (running twice does not error)
- [ ] Test _SCHEMA_VERSION bumped to 3 after migration
- [ ] Test init_db() on fresh DB creates tables with scope column
- [ ] Test Entity(name='x', entity_type='file').scope == 'global' (default)
- [ ] Test Edge(...).scope == 'global' (default)
- [ ] Test Document(...).scope == 'global' (default)
- [ ] Test Entity(scope='project:owlbear') round-trips through model
- [ ] All tests run via: uv run pytest tests/test_knowledge_schema.py tests/test_knowledge_models.py -v
