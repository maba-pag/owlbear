---
id: 1339
title: 'Lifecycle contract reconciliation: expose fail+release in MCP, align 5 layers
  to 9 tools'
status: todo
priority: needed
created: 2026-05-04T15:00:05.806598+00:00
updated: 2026-05-04T15:01:06.364192+00:00
tags:
- sync-blocker
- mcp-kanban
- docs
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Engine, AgentView, MCP, handbook, and README disagree on outcomes and tool count. MCP removed `fail` but pipeline protocol documents it. `create_dr` is tool #9 but missing from handbook table.

Decision (confirmed): Expose both `fail` (records failure) and `release` (silent unclaim) in MCP. Official tool count is 9 (including create_dr).

## Acceptance Criteria

1. MCP server end_work handler accepts `outcome="fail"` and routes to engine.end_work(outcome="fail")
2. MCP server end_work handler still accepts `outcome="release"` and routes to engine.release_task()
3. h-mcp-kanban/SKILL.md Tool Summary table lists 9 tools (add create_dr row)
4. h-mcp-kanban/SKILL.md outcome documentation lists all 5 outcomes: success, reject, fail, block, release — each with "use when" guidance
5. mcp-kanban/README.md matches (9 tools, 5 outcomes documented)
6. No regression in passing MCP tests; currently-red guidance tests that expected fail behavior pass
7. AgentView already supports both — verify no changes needed there

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `share/skills/h-mcp-kanban/SKILL.md`
- `serve/mcp-kanban/README.md`

## Source

Finding 4 in `.owlbear/research/kanban-mcp-deployment-audit.md`