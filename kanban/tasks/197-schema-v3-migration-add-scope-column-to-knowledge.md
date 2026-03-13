---
id: 197
title: Schema v3 migration — add scope column to knowledge tables
status: archived
priority: important
created: 2026-02-28T01:10:07.2099107+01:00
updated: 2026-02-28T23:53:46.1677214+01:00
started: 2026-02-28T01:11:42.786578+01:00
completed: 2026-02-28T23:53:46.1677214+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
class: standard
---

Add scope TEXT DEFAULT 'global' column to entities, documents, edges, chunks, embedding_rowid_map tables. Bump _SCHEMA_VERSION to 3.

File: src/owlbear/memory/knowledge/schema.py

AC:
- [ ] _SCHEMA_VERSION = 3
- [ ] _migrate_v2_to_v3(conn) function: 5x ALTER TABLE ADD COLUMN scope TEXT DEFAULT 'global' wrapped in contextlib.suppress(OperationalError)
- [ ] _migrate_v2_to_v3 creates indexes: idx_entities_scope, idx_documents_scope, idx_embedding_rowid_map_scope
- [ ] _migrate_v2_to_v3 updates schema_version row to 3
- [ ] init_db() calls _migrate_v2_to_v3 when stored version < 3
- [ ] init_db() on fresh DB creates all tables with scope column included in DDL
- [ ] Update _CREATE_ENTITIES, _CREATE_DOCUMENTS, _CREATE_EDGES, _CREATE_CHUNKS, _CREATE_EMBEDDING_ROWID_MAP DDL to include scope column
- [ ] Existing v2 data preserved (scope defaults to 'global')
- [ ] Migration idempotent (safe to run twice)

Pattern: follows existing _migrate_v1_to_v2 in same file.
Depends on: #220 (test task)
See docs/research/knowledge-scoping.md
