---
id: 429
title: Test schema v6 migration -- knowledge_sources table
status: archived
priority: needed
created: 2026-03-02T01:50:52.0280276+01:00
updated: 2026-03-02T09:15:29.5819202+01:00
started: 2026-03-02T01:50:57.0664185+01:00
completed: 2026-03-02T09:15:29.5819202+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD red-phase for #383. Tests for schema v5->v6 migration adding knowledge_sources table.

## Acceptance Criteria
- _SCHEMA_VERSION constant equals 6
- Fresh init_db creates knowledge_sources table with all columns: id, name, source_type, config, scope, enabled, priority, last_refreshed_at, last_error, created_at, updated_at
- Fresh DB has unique index idx_knowledge_sources_name_scope on (name, scope)
- Fresh DB has index idx_knowledge_sources_scope on (scope)
- v5 DB migrated via init_db gains knowledge_sources table (idempotent)
- Existing v5 data (entities, documents, etc.) is preserved after migration
- Double-calling init_db on v6 DB is safe (idempotent)
- schema_version table shows version=6 after migration
- Follow existing migration pattern: _migrate_v5_to_v6 function with contextlib.suppress

Depends on #428 (test #382)
