---
id: 806
title: Add board_config()
status: research
priority: needed
created: '2026-04-10T21:21:14.299574+00:00'
updated: '2026-04-10T21:21:14.299574+00:00'
tags:
- phase-1
- scope:mcp-kanban
- config
- rigor:thorough
parent: 798
depends_on:
- 805
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `board_config()` method on `KanbanEngine`
- Returns `model_copy()` of cached config (valid statuses, priorities, display order)
- Returned object is a defensive copy — mutating it does not affect engine state
- #805 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #805 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`