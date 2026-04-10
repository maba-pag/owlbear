---
id: 780
title: Tests — Schema v9 migration (source_pages, source_id FK)
status: backlog
priority: needed
created: '2026-04-10T12:30:43.970655+00:00'
updated: '2026-04-10T12:30:43.970655+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify v8→v9 migration runs without error on a v8 database
- Tests assert `source_pages` table exists with columns: `id`, `source_id`, `url`, `content_hash`, `last_fetched_at`, `status`, `scope`
- Tests assert `documents` table has `source_id` column, nullable (NULL for legacy rows)
- Tests verify `SCHEMA_VERSION == 9`
- File: `tests/test_schema_v9_775.py`

## Context
- WS-A: Schema + Models Foundation
- Scope item 5 from #775
- See research F2: NULL source_id for legacy, F6: source_pages for Phase 2 readiness
