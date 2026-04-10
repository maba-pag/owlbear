---
id: 826
title: Slim server pick_tasks to thin wrapper
status: research
priority: important
created: '2026-04-10T21:23:21.110689+00:00'
updated: '2026-04-10T21:23:21.110689+00:00'
tags:
- phase-3
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 825
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `server.py` `pick_tasks` MCP tool calls `pick_dispatchable()` from `owlbear_kanban.dispatch`
- No inline gating logic remains in `server.py` (no `_check_pick_gates`, no rank maps)
- Response format unchanged: dispatch wrapper with task details
- Boundary conversion from `Task` to `KanbanTask` happens in server
- #825 tests pass GREEN
- All existing MCP tests pass (O4)

## Context

Phase 3, step 4. Final task. Depends on #825 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`