---
id: 1090
title: 'A-06: GREEN — read tool adapters'
status: todo
priority: critical
created: 2026-04-21T10:54:20.345618+00:00
updated: 2026-04-21T10:54:20.345618+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1086
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.1–§5.3, paper-integration.md §1.1–§1.3
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Implement the 3 read-only MCP tool handlers in server.py: `list_tasks`, `show_task`, `pick_tasks`. Each handler: (1) deserializes MCP call args into the input model, (2) calls the corresponding AgentView method with a 1:1 passthrough, (3) serializes the engine response envelope to MCP response, (4) catches KanbanError and maps to MCP ToolError(user_message). The adapter is mechanical — no business logic.

First GREEN impl task on server.py — establishes the adapter pattern (error mapping helper, AgentView injection) that mutation and lifecycle tasks build on.

## Acceptance Criteria

- [ ] All RED tests from A-03 (#1086) pass
- [ ] `list_tasks` tool registered, forwards all 12 params to AgentView.list_tasks
- [ ] `show_task` tool registered, forwards id + section to AgentView.show_task
- [ ] `pick_tasks` tool registered, forwards wave_size + max_waves to AgentView.pick_tasks
- [ ] KanbanError → ToolError mapping helper established (reused by later tasks)
- [ ] Response envelopes serialized as MCP content (JSON text)
- [ ] No business logic in adapter — all validation delegated to engine