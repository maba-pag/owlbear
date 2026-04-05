---
id: 624
title: Evaluate and clean up orchestrator planner/ package
status: ideation
priority: important
created: 2026-04-05T01:31:32.2092633+02:00
updated: 2026-04-05T01:58:35.1178209+02:00
tags:
    - scope:orchestrator
    - phase-2
    - type:build
parent: 619
depends_on:
    - 621
    - 622
class: standard
---

## Acceptance Criteria

- serve/orchestrator/src/owlbear/planner/ package evaluated for removal:
  - If pick_tasks in kanban server fully replaces the Python code, remove planner/ package
  - If orchestrator loop.py still imports from planner/ directly (in-process path), keep as-is
  - Document decision in parent task #619 body
- If removed:
  - All imports in orchestrator/ updated (loop.py, waves.py)
  - Tests that covered planner/ gates/selector logic verified to still pass via MCP tool tests (#620)
  - No dead imports remaining
- If kept:
  - Add comment explaining dual-path (in-process for loop, MCP for agent) with link to #619
