---
id: 978
title: 'RED: edit_task + end_work guidance integration tests'
status: backlog
priority: needed
created: 2026-04-18T21:18:15.549754+00:00
updated: 2026-04-18T21:18:15.549754+00:00
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

- `edit_task(block="reason")` response includes DR-required message in `guidance`
- `edit_task(block=...)` removes `block:user` tag from task if present
- `end_work(outcome="block", block_reason=...)` response includes DR-required message in `guidance`
- `end_work(outcome="block")` removes `block:user` tag if present
- `end_work(outcome="success")` response includes commit-pushed message in `guidance`
- `edit_task` non-block edit returns empty `guidance`
- `end_work(outcome="fail")` returns empty `guidance`

All tests must FAIL (server.py not yet wired to call collect_guidance).