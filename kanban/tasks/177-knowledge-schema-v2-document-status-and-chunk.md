---
id: 177
title: Knowledge schema v2 — document status and chunk tracking
status: archived
priority: needed
created: 2026-02-27T22:10:15.641287+01:00
updated: 2026-02-28T23:53:26.2695165+01:00
started: 2026-02-27T22:12:01.2393493+01:00
completed: 2026-02-28T23:53:26.2695165+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 188
class: standard
---

Module: src/owlbear/memory/knowledge/schema.py (extend existing) | Test: tests/test_knowledge_schema.py (extend existing) | See docs/research/knowledge-ingestion.md S3.4.

AC:
- New document_status table: document_id TEXT PK, status TEXT, source TEXT, error TEXT, created_at TEXT, updated_at TEXT
- New chunks table: id TEXT PK, document_id TEXT FK->documents(id), chunk_index INTEGER, content TEXT, metadata TEXT, created_at TEXT
- embedding_rowid_map gains optional chunk_id TEXT column to link embeddings to specific chunks
- _SCHEMA_VERSION bumped from 1 to 2
- init_db() creates new tables idempotently (CREATE TABLE IF NOT EXISTS)
- Migration path: if schema_version table shows version=1, ALTER TABLE adds chunk_id column to embedding_rowid_map
- Existing v1 data preserved after migration (non-destructive)
- DDL constants follow existing naming pattern (_CREATE_DOCUMENT_STATUS, _CREATE_CHUNKS)
- ruff clean, all tests in tests/test_knowledge_schema.py pass
