---
id: 1185
title: 'P1-06: Implement pick_tasks resolve integration'
status: research
priority: important
created: 2026-04-30T00:51:51.711195+00:00
updated: 2026-04-30T00:53:11.078605+00:00
tags:
- phase-1
- scope:kanban
- type:impl
parent: 1179
depends_on:
- 1181
- 1184
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `pick_tasks` calls `resolve_pending_drs(engine)` at top of function, before task selection
- Call wrapped in try/except — resolve failures logged but never stall task dispatch
- Existing pick_tasks behavior unchanged when no pending DRs exist
- Graceful handling when pending/ directory doesn't exist (no crash)
- All tests from #1184 pass

## Scope

- IN: pick_tasks function modification only
- OUT: decisions.py internals, MCP tool

Brief: see parent #1179
