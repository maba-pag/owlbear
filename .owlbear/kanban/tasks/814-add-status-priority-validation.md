---
id: 814
title: Add status/priority validation
status: research
priority: needed
created: '2026-04-10T21:22:01.275308+00:00'
updated: '2026-04-10T21:22:01.275308+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 813
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `create_task` raises `ValueError` for invalid status or priority (validated against config-defined values)
- `edit_task` raises `ValueError` for invalid status or priority
- MCP adapter maps `ValueError` to `ToolError` in create_task and edit_task handlers (existing pattern from move_task)
- Valid values accepted without change to existing behavior
- #813 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #813 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`