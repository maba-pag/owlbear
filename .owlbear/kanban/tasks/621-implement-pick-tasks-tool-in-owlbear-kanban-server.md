---
id: 621
title: Implement pick_tasks tool in owlbear-kanban server
status: backlog
priority: needed
created: 2026-04-05T01:31:03.9704718+02:00
updated: 2026-04-05T10:39:37.0259938+02:00
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

[[2026-04-05]] Sun 10:39
## Research
- Research doc: .owlbear/research/pick-tasks-implementation.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Inline gates in server.py, raw-dict approach (confidence: .85)
- Follow-up tasks created: none (subtasks #620–#624 already exist)
- Decision requests: none

## Challenge Results
- Challenger: N/A — T1 implementation task, architecture decided in #619
- Tier: T1 (autonomous) — no new capabilities beyond approved #619 design

## Key Findings for Builder
- mcp-kanban has NO dep on orchestrator; gates must be copied+adapted, not imported
- list_tasks strips body — pick_tasks needs its own _run_kanban call with full JSON
- Body is str|None in KanbanTask — use task.get("body") or "" in gates
- Gate functions work on raw dicts (not Pydantic models) — matches list_tasks pattern
- Sort: (PRIORITY_RANK, STATUS_RANK) ascending, cap at limit (default 25)
- STATUS_AGENT_MAP and crash_failures NOT migrated — orchestrator responsibility
- Return: {"dispatch": [{"task_id": int, "status": str}]}
- Error: ToolError on rc!=0 or JSON parse failure; empty dispatch on all-gates-fail
