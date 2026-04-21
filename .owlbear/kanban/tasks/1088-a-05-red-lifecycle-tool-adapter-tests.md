---
id: 1088
title: 'A-05: RED — lifecycle tool adapter tests'
status: todo
priority: needed
created: 2026-04-21T10:53:58.270590+00:00
updated: 2026-04-21T10:53:58.270590+00:00
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
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.6–§5.8, paper-integration.md §1.6–§1.8
Module: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`

Test the 3 lifecycle tool adapters: `move_task`, `start_work`, `end_work`. All tests mock `AgentView`. Tests verify: correct AgentView method called with correct args, SingleTaskResponse returned, KanbanError → ToolError mapping, and the `end_work` forbidden-parameter matrix (paper-integration.md §1.8).

## Acceptance Criteria

- [ ] `move_task`: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned
- [ ] `move_task`: `status="archived"` without `archival_reason` → engine raises → ToolError (AC4)
- [ ] `start_work`: id forwarded; SingleTaskResponse returned
- [ ] `start_work`: already claimed → engine ConcurrencyError → ToolError
- [ ] `start_work`: archived / blocked → engine raises → ToolError
- [ ] `end_work`: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned
- [ ] `end_work`: outcome="success" auto-advance (AC18); outcome="reject" (AC19); outcome="release" idempotent (AC20)
- [ ] `end_work`: outcome="block" with block_reason (AC-NEW-1, AC-NEW-2); without → ToolError (AC-NEW-2)
- [ ] `end_work`: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason → ToolError (AC-NEW-3, AC-NEW-9, AC-NEW-11, AC-NEW-18)
- [ ] Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message
- [ ] All tests fail (RED phase)