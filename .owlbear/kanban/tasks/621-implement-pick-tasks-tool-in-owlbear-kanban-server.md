---
id: 621
title: Implement pick_tasks tool in owlbear-kanban server
status: ideation
priority: needed
created: 2026-04-05T01:31:03.9704718+02:00
updated: 2026-04-05T01:58:34.7203915+02:00
tags:
    - scope:mcp
    - phase-2
    - type:build
parent: 619
depends_on:
    - 620
class: standard
---

## Acceptance Criteria

- New `pick_tasks` tool registered in owlbear-kanban MCP server (server.py)
- Tool signature: `pick_tasks(limit: int = 25) → dict`
- No filters — zero-config, opinionated about what's eligible
- Gate logic migrated from serve/orchestrator/src/owlbear/planner/gates.py:
  - check_atomicity: word-boundary "and" in title
  - check_tdd: in-progress tasks must have "## Test-Writer Notes"
  - check_clarity: active statuses must have bullet/numbered AC
- Sort logic migrated from serve/orchestrator/src/owlbear/planner/selector.py:
  - PRIORITY_RANK and STATUS_RANK sort keys
  - Cap at limit parameter
- Board reading uses existing _run_kanban with --unblocked --not-blocked --unclaimed flags
- Return format: `{"dispatch": [{"task_id": int, "status": str}]}`
- No agent mapping — orchestrator's responsibility
- No crash_failures — orchestrator's responsibility
- All tests from #620 pass
- Tool added to __all__ in server.py
