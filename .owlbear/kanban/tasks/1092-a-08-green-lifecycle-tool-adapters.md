---
id: 1092
title: 'A-08: GREEN — lifecycle tool adapters'
status: todo
priority: critical
created: '2026-04-21 10:54:37.271169+00:00'
updated: '2026-04-21 10:54:37.271169+00:00'
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1088
- 1091
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.6–§5.8, paper-integration.md §1.6–§1.8
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Implement the 3 lifecycle MCP tool handlers in server.py: `move_task`, `start_work`, `end_work`. Same mechanical adapter pattern. `end_work` is the most complex tool — 7 params, 4 outcomes, forbidden-parameter matrix — but all validation is in the engine. The adapter forwards and maps errors. Serialized after mutation tools on server.py.

## Acceptance Criteria

- [ ] All RED tests from A-05 (#1088) pass
- [ ] `move_task` tool registered, forwards id, status, archival_reason, archival_refs to AgentView.move_task
- [ ] `start_work` tool registered, forwards id to AgentView.start_work
- [ ] `end_work` tool registered, forwards all 7 params (id, outcome, move_to, note, block_reason, archival_reason, archival_refs) to AgentView.end_work
- [ ] `end_work` forbidden-parameter matrix enforced by engine — adapter just forwards and maps errors
- [ ] Error mapping reuses the helper established in A-06 (#1090)
- [ ] No business logic in adapter — all archival validation, predicate checks, claim state managed by engine