---
id: 1087
title: 'A-04: RED — mutation tool adapter tests'
status: todo
priority: needed
created: 2026-04-21T10:53:48.099115+00:00
updated: 2026-04-21T10:53:48.099115+00:00
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
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.4–§5.5, paper-integration.md §1.4–§1.5
Module: `serve/mcp-kanban/tests/test_mcp_mutation_tools.py`

Test the 2 mutation tool adapters: `create_task`, `edit_task`. All tests mock `AgentView`. Tests verify: correct AgentView method called with correct args, SingleTaskResponse returned, KanbanError → ToolError mapping.

## Acceptance Criteria

- [ ] `create_task`: title, body, priority, tags, parent, depends_on forwarded; SingleTaskResponse returned (AC24 — dep validation delegated to engine)
- [ ] `create_task`: no `status` param accepted (engine controls entry status per D50)
- [ ] `edit_task`: all 13 params forwarded; SingleTaskResponse returned
- [ ] `edit_task`: `body` + `append_body` both set → engine raises ValidationError → adapter maps to ToolError (AC14)
- [ ] `edit_task`: `archival_reason` / `archival_refs` on non-archived → engine raises → ToolError
- [ ] `edit_task`: no-op call → engine raises → ToolError
- [ ] Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message
- [ ] All tests fail (RED phase)