---
id: 1086
title: 'A-03: RED — read tool adapter tests'
status: todo
priority: needed
created: 2026-04-21T10:53:39.529461+00:00
updated: 2026-04-21T10:53:39.529461+00:00
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
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.1–§5.3, paper-integration.md §1.1–§1.3
Module: `serve/mcp-kanban/tests/test_mcp_read_tools.py`

Test the 3 read-only tool adapters: `list_tasks`, `show_task`, `pick_tasks`. All tests mock `AgentView` — the adapter is a mechanical translator; engine behavior is Brief B's responsibility. Tests verify: correct AgentView method called with correct args, response envelope returned unmodified, KanbanError subclasses mapped to MCP ToolError with `user_message`.

## Acceptance Criteria

- [ ] `list_tasks`: all params forwarded to AgentView.list_tasks; ListTasksResponse returned
- [ ] `list_tasks`: `ids` exclusivity enforced (AC15) — adapter or engine raises, adapter maps to ToolError
- [ ] `show_task`: id + section forwarded; ShowTaskResponse returned including `missing_sections` case (AC11)
- [ ] `show_task`: missing id → ToolError (AC via engine NotFoundError mapping)
- [ ] `pick_tasks`: wave_size + max_waves forwarded; PickTasksResponse with waves returned (AC22, AC23)
- [ ] Error mapping: engine ValidationError → MCP ToolError with user_message
- [ ] Error mapping: engine NotFoundError → MCP ToolError with user_message
- [ ] All tests fail (RED phase)