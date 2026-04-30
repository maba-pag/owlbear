---
id: 1183
title: 'P1-04: Implement create_dr MCP tool + guidance text update'
status: research
priority: needed
created: 2026-04-30T00:51:43.218458+00:00
updated: 2026-04-30T00:53:02.790321+00:00
tags:
- phase-1
- scope:mcp-kanban
- type:impl
parent: 1179
depends_on:
- 1181
- 1182
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `create_dr` tool registered in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- Tool delegates to `decisions.create_dr()` from the kanban engine package
- Tool response shape: `{created: true, path: str}` on success, error on failure
- request_type validated to enum (decision|action) at MCP layer
- Guidance text in `guidance.py` updated: "via the scribe agent" → "via the create_dr tool"
- All tests from #1182 pass

## Scope

- IN: MCP tool wiring + guidance string update
- OUT: decisions.py internals, pick_tasks

Brief: see parent #1179
