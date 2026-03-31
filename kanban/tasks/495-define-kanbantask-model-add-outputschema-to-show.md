---
id: 495
title: Define KanbanTask model + add outputSchema to show/move/pick
status: ideation
priority: needed
created: 2026-03-31T06:47:09.5895363+02:00
updated: 2026-03-31T06:47:09.5895363+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
depends_on:
    - 489
class: standard
---

## Acceptance Criteria

- [ ] Define KanbanTask(BaseModel) in packages/mcp-kanban/src/owlbear_mcp_kanban/models.py
- [ ] Fields match kanban-md JSON schema (id, title, status, priority, created, updated, + optional fields)
- [ ] show_task returns KanbanTask (change return type from str, add json.loads + model_validate)
- [ ] move_task returns KanbanTask (after --json switch in #489)
- [ ] pick_task returns KanbanTask (after --json switch in #489)
- [ ] Error handling: raise ToolError(stderr) instead of return error string for structured tools
- [ ] FastMCP auto-generates outputSchema from KanbanTask return type
- [ ] structuredContent returned alongside text content in CallToolResult
- [ ] Tests verify: outputSchema present in tool listing, structuredContent in responses
- [ ] ruff clean

## Context
Follows #489 (--json switch). See docs/research/mcp-kanban-outputschema-annotations.md
FastMCP auto-derives outputSchema from Pydantic BaseModel return types.
Error handling switches from 'return error:...' to 'raise ToolError(...)' per MCP spec.
