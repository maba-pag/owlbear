---
id: 1338
title: 'Fix migration/storage suites: prove old-to-new schema round-trip before sync'
status: todo
priority: needed
created: 2026-05-04T15:00:05.755705+00:00
updated: 2026-05-04T15:01:06.357699+00:00
tags:
- sync-blocker
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Storage now emits grouped schema (storage.py L171–174) but migration and compatibility tests are red. Must prove old-format boards can be read/migrated without data loss before syncing to main.

## Acceptance Criteria

1. test_migrate.py passes (all migration tests green)
2. test_storage_1050.py passes (storage compat tests green)
3. test_storage.py passes (core storage tests green)
4. test_engine_atomicity_1104.py passes (atomicity with new schema green)
5. Round-trip test: old-format board → engine loads → saves → old-format reader can still parse (or explicit migration converts cleanly)

## Key Files

- `serve/kanban/src/owlbear_kanban/storage.py`
- `serve/kanban/src/owlbear_kanban/migrate.py`
- `serve/kanban/tests/test_storage_1050.py`
- `serve/kanban/tests/test_storage.py`
- `serve/kanban/tests/test_migrate.py`

## Source

Finding 3 in `.owlbear/research/kanban-mcp-deployment-audit.md`