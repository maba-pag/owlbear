---
id: 804
title: Add refresh_config + fix config staleness
status: research
priority: needed
created: '2026-04-10T21:21:04.269881+00:00'
updated: '2026-04-10T21:21:04.269881+00:00'
tags:
- phase-1
- scope:mcp-kanban
- config
- rigor:thorough
parent: 798
depends_on:
- 803
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `refresh_config()` method on `KanbanEngine`: reloads config from disk, updates `self._config` + all derived state (tasks_dir, archive_dir, rank maps)
- `create_task` calls `refresh_config()` internally (or equivalent) to ensure fresh config for `next_id`
- After `refresh_config()`, `_status_rank()` and `_priority_rank()` use new config values
- #803 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #803 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`