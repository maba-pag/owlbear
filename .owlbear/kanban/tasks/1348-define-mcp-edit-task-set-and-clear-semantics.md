---
id: 1348
title: Define MCP edit_task set and clear semantics
status: backlog
priority: critical
created: 2026-05-04T18:17:29.586768+00:00
updated: 2026-05-04T18:17:29+00:00
tags:
- sync-blocker
- mcp-kanban
- kanban
- api-contract
parent:
depends_on:
- 1339
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

MCP `edit_task`, `EditTaskParams`, `AgentView.edit_task()`, and raw `KanbanEngine.edit_task()` disagree on nullable edit semantics. The current public MCP path cannot clearly distinguish omitted, set-empty, and clear operations for important fields. In practice, `body=""` is treated as no change, `parent=0` is treated as no change, `parent=None` cannot clear through AgentView, and MCP has no title edit surface even though the raw engine can update titles.

Audit decision: create a dedicated MCP/AgentView edit-contract task instead of hiding this inside the Cockpit edit workflow.

## Acceptance Criteria

1. Define and implement explicit MCP/AgentView semantics for omitted vs set vs clear fields.
2. `body=None` or omitted means no body change; `body=""` intentionally clears the body; non-empty `body` replaces the body.
3. Parent can be set to a positive existing task ID and can also be cleared through an explicit unambiguous contract, such as `clear_parent=true` or equivalent field-presence handling proven by tests.
4. MCP exposes task title editing, or the task records an explicit decision that title changes are intentionally not part of the MCP edit surface.
5. Status changes remain routed through `move_task`; `edit_task` must not create a second status mutation path unless explicitly approved.
6. No-op detection still raises `ERR_NO_OP` when a request contains no effective mutation.
7. Invalid clear/set combinations return clear validation errors and do not mutate storage.
8. `EditTaskParams`, MCP tool signatures, AgentView behavior, docs/handbook examples, and metadata patches agree on the final contract.
9. Durable tests cover clearing body, setting body to a non-empty value, clearing parent, setting parent, title edit or explicit title-exclusion decision, and no-op behavior.

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `serve/kanban/src/owlbear_kanban/engine.py`
- `share/skills/h-mcp-kanban/SKILL.md`
- `serve/mcp-kanban/README.md`
- `serve/mcp-kanban/tests/`
- `serve/kanban/tests/`

## Audit Evidence

- MCP server `edit_task` uses `body: str = ""` and only forwards `body` when truthy.
- MCP server and AgentView use `parent: int = 0` / `parent > 0`, so parent can be set but not cleared through the public facade.
- `EditTaskParams` advertises nullable `body` and `parent`, but the live tool signature does not faithfully expose clear semantics.
- Raw engine title mutation exists, while MCP/AgentView omit title from edit semantics.

## Source

Deployment audit finding group 6, 2026-05-04.
