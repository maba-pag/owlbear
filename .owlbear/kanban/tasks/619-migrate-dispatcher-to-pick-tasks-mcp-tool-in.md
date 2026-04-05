---
id: 619
title: Migrate dispatcher to pick_tasks MCP tool in owlbear-kanban
status: ideation
priority: needed
created: 2026-04-05T01:30:40.2393944+02:00
updated: 2026-04-05T01:58:24.4547464+02:00
tags:
    - scope:mcp
    - scope:orchestrator
    - phase-2
    - type:restructure
class: standard
---

## Summary

Replace the dispatcher agent (share/agents/dispatcher.agent.md) with a `pick_tasks` MCP tool inside the owlbear-kanban server. The dispatcher workflow is fully deterministic (`disable-model-invocation: true`) and the Python implementation already exists in serve/orchestrator/src/owlbear/planner/.

## Motivation

- Dispatcher uses zero LLM reasoning — it's pure function: board_state → dispatch list
- Current path: orchestrator → subagent call → agent context load → MCP calls → JSON output → parse
- Target path: orchestrator → single MCP tool call → JSON result
- Eliminates agent infrastructure overhead for a deterministic computation
- Tested Python code already exists in planner/ package (gates.py, selector.py, board.py, models.py)

## Scope

- New `pick_tasks` tool in owlbear-kanban MCP server
- Orchestrator agent updated to call tool directly (crash_failures filtering and agent mapping stay in orchestrator)
- Dispatcher agent deprecated and removed from orchestrator
- w-dispatch-planning skill archived (or kept as design doc)

## Architecture Decision

Tool signature:
```
pick_tasks(limit: int = 25) → {"dispatch": [{"task_id": int, "status": str}]}
```

One parameter: limit (default 25). No filters — the tool is zero-config and opinionated about what's eligible.

Logic: read board (unblocked, not-blocked, unclaimed) → apply gates (atomicity, TDD, clarity) → sort by priority then pipeline proximity → cap at limit → return task_id + status.

Agent mapping stays in orchestrator (status → agent is orchestrator's responsibility).
Crash failure exclusion stays in orchestrator loop (cycle-specific state).
Gate logic migrates from planner/gates.py. Sort logic from planner/selector.py.
Board reading reuses existing _run_kanban infrastructure.

Subtasks: #620-#624.
