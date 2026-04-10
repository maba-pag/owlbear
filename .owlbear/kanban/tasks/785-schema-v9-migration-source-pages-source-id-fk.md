---
id: 785
title: Schema v9 migration (source_pages, source_id FK)
status: backlog
priority: needed
created: '2026-04-10T12:31:05.190224+00:00'
updated: '2026-04-10T12:31:05.190224+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 780
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `schema.py` `SCHEMA_VERSION = 9`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (INTEGER PRIMARY KEY), `source_id` (INTEGER REFERENCES knowledge_sources(id)), `url` (TEXT NOT NULL), `content_hash` (TEXT), `last_fetched_at` (TEXT), `status` (TEXT NOT NULL DEFAULT 'pending'), `scope` (TEXT NOT NULL)
- `_migrate_v8_to_v9()` adds `source_id INTEGER REFERENCES knowledge_sources(id)` to `documents` (NULL default, no backfill)
- `_SCOPE_TABLES` updated to include `source_pages`
- All #780 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/schema.py`

## Context
- WS-A: Schema + Models Foundation
- Scope item 5 from #775
- See research F2: NULL source_id for legacy, F6: source_pages ships for Phase 2 readiness
