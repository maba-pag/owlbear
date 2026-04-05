---
id: 188
title: Test knowledge schema v2 — document status and chunk tables
status: archived
priority: needed
created: 2026-02-27T22:17:40.699715+01:00
updated: 2026-02-28T23:53:37.8356109+01:00
started: 2026-02-27T23:12:02.4795857+01:00
completed: 2026-02-28T23:53:37.8356109+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

Extend tests in tests/test_knowledge_schema.py for schema v2 changes in src/owlbear/memory/knowledge/schema.py. Test: (1) init_db creates document_status table (document_id PK, status, source, error, created_at, updated_at) (2) init_db creates chunks table (id PK, document_id FK, chunk_index, content, metadata, created_at) (3) embedding_rowid_map gains chunk_id column (4) schema_version writes version=2 (5) Calling init_db on fresh DB creates all v2 tables idempotently (6) Migration from v1: ALTER TABLE adds chunk_id column to embedding_rowid_map if not present (7) Existing v1 data is preserved after migration
