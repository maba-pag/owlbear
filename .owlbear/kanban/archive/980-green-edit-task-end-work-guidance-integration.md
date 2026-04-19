---
id: 980
title: 'GREEN: edit_task + end_work guidance integration'
status: backlog
priority: needed
created: 2026-04-18T21:18:27.029383+00:00
updated: 2026-04-18T21:18:27.029383+00:00
tags:
- scope:mcp
- scope:kanban
- type:build
parent: 973
depends_on:
- 978
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase. Makes #978 tests pass.

## Acceptance Criteria
File: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

- `edit_task` block branch: after engine call, invoke `collect_guidance("edit_block", before, after)` and attach to returned `KanbanTask.guidance`. Also remove `block:user` tag from task tags (agent re-blocking takes ownership per D3).
- `end_work` block path: invoke `collect_guidance("end_work_block", ...)`; remove `block:user` tag.
- `end_work` success path: invoke `collect_guidance("end_work_success", ...)`.
- All other paths return empty `guidance`.

All tests in #978 pass; all existing kanban MCP tests still pass.