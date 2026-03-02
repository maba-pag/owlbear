---
id: 383
title: Schema v6 migration -- knowledge_sources table
status: archived
priority: needed
created: 2026-03-01T20:15:01.9145596+01:00
updated: 2026-03-02T09:14:46.9869353+01:00
started: 2026-03-01T20:23:00.0699047+01:00
completed: 2026-03-02T09:14:46.9869353+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 429
class: standard
---

From #254 source-registry-research.md. Add knowledge_sources table to schema.py as schema v6.

NOTE: Current schema is v5 (chunk_id on entities, from task #371). This task bumps to v6.

## Location
- src/owlbear/memory/knowledge/schema.py

## Acceptance Criteria
- _SCHEMA_VERSION bumped from 5 to 6
- New DDL constant _CREATE_KNOWLEDGE_SOURCES with columns: id TEXT PRIMARY KEY, name TEXT NOT NULL, source_type TEXT NOT NULL, config TEXT NOT NULL (JSON), scope TEXT DEFAULT 'global', enabled INTEGER DEFAULT 1, priority INTEGER DEFAULT 0, last_refreshed_at TEXT, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
- New _migrate_v5_to_v6(conn) function: CREATE TABLE IF NOT EXISTS knowledge_sources (idempotent), CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_name_scope ON knowledge_sources(name, scope), CREATE INDEX IF NOT EXISTS idx_knowledge_sources_scope ON knowledge_sources(scope), UPDATE schema_version SET version=6
- init_db: fresh databases include knowledge_sources in CREATE sequence
- init_db: existing v5 databases auto-migrate via _migrate_v5_to_v6
- init_db: migration chain: if current < 6: _migrate_v5_to_v6(conn)
- All existing data (entities, documents, chunks, edges, document_status) preserved after migration
- Double-calling init_db is safe (idempotent)
- Follows exact same pattern as _migrate_v4_to_v5

Depends on test task #429, #382.
