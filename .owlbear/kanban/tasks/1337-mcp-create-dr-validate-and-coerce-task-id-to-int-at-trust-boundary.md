---
id: 1337
title: 'MCP create_dr: validate and coerce task_id to int at trust boundary'
status: todo
priority: critical
created: 2026-05-04T15:00:05.722955+00:00
updated: 2026-05-04T15:08:59.559773+00:00
tags:
- sync-blocker
- security
- mcp-kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-04T15:08:59.559773+00:00
archival_reason:
archival_refs: []
---

## Context

`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (L369–387) accepts task_id as raw string. `serve/kanban/src/owlbear_kanban/decisions.py` expects int and uses it in filename construction. Non-numeric input is never rejected — path traversal possible.

## Acceptance Criteria

1. MCP create_dr handler coerces task_id to int; non-numeric raises ValueError with clear message
2. Integration test proves path-traversal payloads are rejected (e.g., "../etc/passwd", "1; rm -rf", "abc")
3. All red tests in test_mcp_kanban_1196 and test_mcp_create_dr_1182 pass
4. Existing valid integer task_ids continue to work

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/kanban/src/owlbear_kanban/decisions.py`

## Source

Finding 2 in `.owlbear/research/kanban-mcp-deployment-audit.md`