---
id: 1076
title: 'B-14: GREEN — pick_tasks'
status: todo
priority: needed
created: 2026-04-21T10:49:32.330314+00:00
updated: 2026-04-21T10:49:32.330314+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1074
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.3
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.pick_tasks — the 4-step dispatcher pipeline codifying `w-orchestration/SKILL.md` Wave Assembly. B-19 (orchestration skill rewrite) depends on this task.

Algorithm: (1) Filter — exclude claimed, archived, dep_status=="blocked", blocked==true (D42+D58). (2) Sort — priority_rank ASC, age DESC, id ASC (D60). (3) Greedy wave assembly — size constraint, intra-wave dep-disjointness, agent-compatibility matrix (D62+D63). (4) Return PickTasksResponse with waves and guidance.

## Acceptance Criteria

- [ ] All RED tests from B-13 (#1074) pass
- [ ] Filter excludes claimed, archived, dep_status=="blocked", blocked==true
- [ ] Sort deterministic: priority_rank(BoardConfig.priorities index) ASC, age DESC, id ASC
- [ ] Greedy assembly: three constraints per wave (size, dep-disjoint, agent-compatible)
- [ ] Output: ≤ max_waves waves, each ≤ wave_size tasks
- [ ] DispatchEntry.agent set from BoardConfig.agent_map[task.status]
- [ ] Default wave_size from BoardConfig.wave_size; max_waves default 3
- [ ] pick_tasks lives on AgentView only (not CockpitView) per D59-revised