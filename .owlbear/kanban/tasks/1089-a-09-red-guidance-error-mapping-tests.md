---
id: 1089
title: 'A-09: RED — guidance + error mapping tests'
status: todo
priority: needed
created: 2026-04-21T10:54:09.278833+00:00
updated: 2026-04-21T10:54:09.278833+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:red
parent: 1045
depends_on:
- 1085
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §7 "guidance field", paper-integration.md §3.6–§3.7
Module: `serve/mcp-kanban/tests/test_mcp_guidance.py`

Test guidance field passthrough and the KanbanError → MCP ToolError error-mapping layer. Guidance is an engine-generated `list[str]` on every response envelope — the adapter must pass it through unmodified. Error mapping: every KanbanError subclass (ValidationError, NotFoundError, ConcurrencyError) maps to MCP `ToolError(user_message)`. Tests mock AgentView.

## Acceptance Criteria

- [ ] Guidance passthrough: engine returns guidance strings → adapter includes them in MCP response unmodified
- [ ] show_task section occurrence count guidance (AC12) passes through
- [ ] pick_tasks dispatch hints pass through
- [ ] create_task/edit_task body size warning (>100 KB) passes through
- [ ] move_task / end_work skip-transition warning passes through (AC-NEW-5)
- [ ] end_work(outcome="block") Action-Request/Decision-Request hint passes through (AC-NEW-4)
- [ ] Error mapping: ValidationError → ToolError (user_message only, no code on wire per §7)
- [ ] Error mapping: NotFoundError → ToolError
- [ ] Error mapping: ConcurrencyError → ToolError (e.g. already-claimed)
- [ ] All tests fail (RED phase)