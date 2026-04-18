---
id: 981
title: 'GREEN: move_task guidance + pre-read'
status: backlog
priority: needed
created: 2026-04-18T21:18:27.039443+00:00
updated: 2026-04-18T21:18:27.039443+00:00
tags:
- scope:mcp
- scope:kanban
- type:build
parent: 973
depends_on:
- 979
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase. Makes #979 tests pass.

## Acceptance Criteria
File: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Per D6:
- `move_task` pre-reads current task via `_show_validated()` to capture `before.status`.
- After engine `move_task` call, invoke `collect_guidance("move", before, after)`.
- Attach result to returned `KanbanTask.guidance`.
- Status ordering pulled from `engine.board_config().statuses` (expose publicly if not already).
- Archived status excluded from skip detection.

All tests in #979 pass; all existing kanban MCP tests still pass.

## Note
If `engine.board_config()` is not currently public, expose it as a property/method (no breaking changes). Document in commit message.