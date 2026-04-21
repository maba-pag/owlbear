---
id: 1074
title: 'B-13: RED — pick_tasks tests'
status: todo
priority: needed
created: 2026-04-21T10:49:15.735084+00:00
updated: 2026-04-21T10:49:15.735084+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1072
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.3, §3.3, §4
Module: `serve/kanban/tests/test_engine_pick_tasks.py`

Test AgentView.pick_tasks — the 4-step dispatcher pipeline: filter (exclude claimed/archived/blocked/dep-blocked per D42+D58), sort (priority_rank ASC, age DESC, id ASC per D60), greedy wave assembly with size/dep-disjointness/agent-compatibility constraints (D63), cardinality limits.

## Acceptance Criteria

- [ ] AC22: `pick_tasks()` returns ≤3 waves; no intra-wave dep edges; no claimed; no archived; no `dep_status="blocked"`; no `blocked==true` (D58)
- [ ] AC23: Each DispatchEntry includes computed `agent` per BoardConfig.agent_map (D24)
- [ ] AC27: Task with dep on wontfix-archived → dep_status="blocked", excluded from pick_tasks
- [ ] AC28: Task with dep on deprecated-archived → dep_status="redirect" (not excluded)
- [ ] wave_size < 1 or max_waves < 1 → ValidationError(ERR_INVALID_WAVE_PARAM)
- [ ] Default wave_size falls back to BoardConfig.wave_size (D42)
- [ ] Sort: priority_rank ASC, age DESC, id ASC (deterministic) per D60
- [ ] Greedy wave assembly: three constraints (size, dep-disjointness, agent-compatibility) per D62+D63
- [ ] Task not fitting any wave and max_waves reached → dropped from this cycle
- [ ] pick_tasks is on AgentView, NOT CockpitView
- [ ] All tests fail (RED phase)