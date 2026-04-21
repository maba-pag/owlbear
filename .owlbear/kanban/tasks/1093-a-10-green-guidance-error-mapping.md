---
id: 1093
title: 'A-10: GREEN — guidance + error mapping'
status: todo
priority: needed
created: 2026-04-21T10:54:47.282679+00:00
updated: 2026-04-21T10:54:47.282679+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1089
- 1092
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §7 "guidance field", paper-integration.md §3.6–§3.7
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` (if needed), `server.py` (integration)

Implement guidance passthrough and finalize the KanbanError → MCP ToolError error-mapping layer. By this point all 8 tool handlers exist — this task ensures guidance strings flow through every response and the error mapping is complete and consistent. May be a no-op if A-06 through A-08 already established the patterns correctly — in that case, this task validates the pattern holds across all tools.

## Acceptance Criteria

- [ ] All RED tests from A-09 (#1089) pass
- [ ] Every tool's MCP response includes `guidance: list[str]` from engine envelope
- [ ] Guidance strings are NOT modified, filtered, or truncated by the adapter
- [ ] Error mapping covers all KanbanError subclasses: ValidationError, NotFoundError, ConcurrencyError
- [ ] ToolError carries `user_message` only — no engine error `code` on the MCP wire (per Brief A §7)
- [ ] AC12: show_task section occurrence count guidance passes through
- [ ] AC-NEW-4: end_work(block) Action-Request hint passes through
- [ ] AC-NEW-5: skip-transition warning passes through