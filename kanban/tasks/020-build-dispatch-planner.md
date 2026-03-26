---
id: 20
title: Build dispatch planner
status: ideation
priority: needed
created: 2026-03-26T17:22:22.8937692+01:00
updated: 2026-03-26T17:25:19.23802+01:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 19
    - 14
class: standard
---

## Objective
Build the dispatch planner that reads the kanban board, selects the next task and appropriate agent, and formats the prompt for Copilot CLI.

## Acceptance Criteria
- [ ] Module in packages/orchestrator/src/owlbear/planner/
- [ ] read_board() - reads kanban state via mcp-kanban tools or direct kanban-md
- [ ] select_task() - picks the highest priority actionable task respecting depends_on
- [ ] select_agent() - maps task status to appropriate agent role
- [ ] format_prompt() - builds the agent prompt with task AC, context, and instructions
- [ ] Dispatch loop: read board, select, dispatch via ACP, update board on completion
- [ ] Respects task dependencies (depends_on field)
- [ ] Respects task priorities
- [ ] Logs each dispatch decision
- [ ] Unit tests for selection logic

## Context
Depends on O1 (ACP client) and M1 (mcp-kanban). The planner is the brain of the orchestrator - it decides what to work on next and delegates to the right agent.
