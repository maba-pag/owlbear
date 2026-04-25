---
id: 1091
title: 'A-07: GREEN — mutation tool adapters'
status: todo
priority: critical
created: '2026-04-21 10:54:28.949075+00:00'
updated: '2026-04-21 10:54:28.949075+00:00'
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1087
- 1090
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.4–§5.5, paper-integration.md §1.4–§1.5
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Implement the 2 mutation MCP tool handlers in server.py: `create_task`, `edit_task`. Same mechanical adapter pattern as read tools: deserialize → AgentView call → serialize response → catch KanbanError → ToolError. Serialized after read tools on server.py to avoid merge conflicts.

## Acceptance Criteria

- [ ] All RED tests from A-04 (#1087) pass
- [ ] `create_task` tool registered, forwards title, body, priority, tags, parent, depends_on to AgentView.create_task
- [ ] `create_task` does NOT accept `status` param (D50 — engine controls entry status)
- [ ] `edit_task` tool registered, forwards all 13 params to AgentView.edit_task
- [ ] `edit_task` does NOT accept `status` param (AC13 — adapter-layer rejection, symmetric with Cockpit AC-NEW-24)
- [ ] Error mapping reuses the helper established in A-06 (#1090)
- [ ] No business logic in adapter