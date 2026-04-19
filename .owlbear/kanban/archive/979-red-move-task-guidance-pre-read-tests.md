---
id: 979
title: 'RED: move_task guidance + pre-read tests'
status: backlog
priority: needed
created: 2026-04-18T21:18:15.559609+00:00
updated: 2026-04-18T21:18:15.559609+00:00
tags:
- scope:mcp
- scope:kanban
- type:test
parent: 973
depends_on:
- 976
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. RED phase. Depends on guidance module from #976.

## Acceptance Criteria
File: `serve/mcp-kanban/tests/test_guidance_integration.py`

- `move_task` to a status > 1 slot ahead of prior status returns forward-skip message in `guidance`
- `move_task` to adjacent status (1-slot forward) returns empty `guidance`
- `move_task` backward returns empty `guidance`
- `move_task` to "archived" returns empty `guidance` (archive is excluded from skip detection per D6)
- `move_task` pre-reads the prior status via `_show_validated()` before calling engine

All tests must FAIL (server.py not yet wired with pre-read + collect_guidance).